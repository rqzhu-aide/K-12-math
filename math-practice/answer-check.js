/* Explicit answer formats only. Unrecognized symbolic/open answers need review. */
(function (root) {
  'use strict';
  function normal(value) { return value.normalize('NFKC').replace(/−/g, '-').replace(/\s+/g, '').toLowerCase(); }
  function decimal(value) {
    var m=value.trim().match(/^([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:e([+-]?\d+))?$/i);
    if (!m || Math.abs(Number(m[3] || 0))>308) throw new Error('Unsupported number');
    var digits=m[2].split('.'), scale=(digits[1] || '').length-Number(m[3] || 0);
    var n=BigInt((digits[0] || '0')+(digits[1] || ''))*(m[1]==='-'?-1n:1n);
    return scale>=0?{n:n,d:10n**BigInt(scale)}:{n:n*10n**BigInt(-scale),d:1n};
  }
  function numbers(value) {
    return value.normalize('NFKC').replace(/−/g, '-').split(',').map(function (item) {
      var parts=item.trim().split('/');
      if (parts.length>2) throw new Error('Unsupported number');
      var a=decimal(parts[0]),b=parts.length===2?decimal(parts[1]):{n:1n,d:1n};
      if (!b.n) throw new Error('Zero denominator');
      return {n:a.n*b.d*(b.n<0n?-1n:1n),d:a.d*(b.n<0n?-b.n:b.n)};
    });
  }
  function formText(value) {
    var text=normal(value);
    for (var pair of [['\\(','\\)'],['$','$']]) {
      if (text.startsWith(pair[0]) && text.endsWith(pair[1])) return text.slice(pair[0].length,-pair[1].length);
    }
    return text;
  }
  function formFeedback(q, answer) {
    if (typeof answer !== 'string') return '';
    var text=formText(answer);
    if (q.answerForm==='decimal' && !/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$/.test(text)) return 'Write your final answer as a decimal numeral rather than a fraction or expression.';
    if (q.answerForm==='standard-monomial' && !/^[+-]?(?:[0-9]+(?:\.[0-9]*)?)?[a-z]+$/.test(text)) return 'Write the numerical coefficient first and omit multiplication signs between the coefficient and letters.';
    if (q.answerForm==='ordered-list') {
      try {
        var a=numbers(text.replace(/^\(|\)$/g,'')),b=numbers(q.answer);
        var equal=function(x,y){return x.n*y.d===y.n*x.d;};
        var compare=function(x,y){var d=x.n*y.d-y.n*x.d;return d<0n?-1:d>0n?1:0;};
        if (a.length===b.length && !a.every(function(x,i){return equal(x,b[i]);})) {
          a.sort(compare); b.sort(compare);
          if (a.every(function(x,i){return equal(x,b[i]);})) return 'Write the values in the order requested in the problem.';
        }
      } catch (_) {}
    }
    return '';
  }
  function enforceForm(q, answer, category) { return category==='correct' && formFeedback(q,answer) ? 'partial' : category; }
  function gradingNotice(q) {
    if (typeof q.gradingNote === 'string' && q.gradingNote.trim()) return q.gradingNote;
    var source=q.gradingStatus==='disputed'?q:q.knowledgeGraph;
    return source && source.gradingStatus==='disputed'
      ? source.gradingNote || 'This problem is available for study without grading.' : null;
  }
  function classify(q, answer) {
    if (gradingNotice(q)!==null) return 'not_graded';
    var kind = q.responseType || 'choice';
    var accepted = responses(q);
    if (kind === 'multiSelect') {
      if (!Array.isArray(answer)) return 'wrong';
      if (!answer.length) return null;
      if (new Set(answer).size !== answer.length || answer.some(function(id){return typeof id !== 'string' || !Object.prototype.hasOwnProperty.call(q.choices || {}, id);})) return 'wrong';
      if (accepted.some(function(set){return same(answer,set);})) return 'correct';
      return accepted.some(function(set){return answer.length < set.length && answer.every(function(id){return set.indexOf(id)>=0;});}) ? 'partial' : 'wrong';
    }
    if (typeof answer !== 'string') return null;
    if ((q.rejectedAnswers || []).some(function(x){return normal(x)===normal(answer);})) return 'wrong';
    if (kind === 'choice') return accepted.indexOf(answer)>=0 ? 'correct' : 'wrong';
    if (kind === 'self') return null;
    if (kind === 'short') {
      if (accepted.some(function(x){return normal(x)===normal(answer);})) return enforceForm(q,answer,'correct');
      if (q.answerForm==='standard-monomial') {
        var withoutSigns=formText(answer).replace(/\*|·|×|\\times|\\cdot/g,'');
        if (accepted.some(function(x){return formText(x)===withoutSigns;})) return formFeedback(q,answer)?'partial':'correct';
      }
      return null;
    }
    if (kind !== 'numeric') return null;
    var rank={wrong:0, unresolved:1, partial:2, correct:3};
    return accepted.reduce(function(best,expected){
      var category=numericCategory(Object.assign({},q,{answer:expected}),answer);
      return rank[category || 'unresolved']>rank[best || 'unresolved'] ? category : best;
    }, accepted.length ? 'wrong' : null);
  }
  function numericCategory(q, answer) {
    var a,b;
    try { a=numbers(answer);b=numbers(q.answer); } catch (_) { return null; }
    var close = function(x,y) { var d=x.n*y.d-y.n*x.d; return (d<0n?-d:d)*1000000000n<=x.d*y.d; };
    var compare = function(x,y) { var d=x.n*y.d-y.n*x.d; return d<0n?-1:d>0n?1:0; };
    if (q.unorderedAnswers || q.answerForm==='ordered-list') {
      var inOrder=a.length===b.length && a.every(function(x,i){return close(x,b[i]);});
      a.sort(compare); b.sort(compare);
      for (var value of a) {
        var i = b.findIndex(function(x){return close(value,x);});
        if (i < 0) return 'wrong';
        b.splice(i,1);
      }
      return b.length || (q.answerForm==='ordered-list' && !inOrder) ? 'partial' : enforceForm(q,answer,'correct');
    }
    if (a.length < b.length) return a.every(function(x,i){return close(x,b[i]);}) ? 'partial' : null;
    if (a.length === b.length && a.every(function (x, i) { return close(x,b[i]); })) return enforceForm(q,answer,'correct');
    return 'wrong';
  }
  function responses(q) {
    if (Array.isArray(q.acceptedResponses)) return q.acceptedResponses;
    return [q.answer].concat(q.responseType==='short' ? q.acceptedAnswers || [] : []).filter(function(x){return typeof x==='string' && x.length;});
  }
  function same(a,b) {
    if (!Array.isArray(a) || !Array.isArray(b)) return a===b;
    if (a.length!==b.length) return false;
    var left=a.slice().sort(),right=b.slice().sort();
    return left.every(function(value,i){return value===right[i];});
  }
  function hasAnswer(value) { return Array.isArray(value) ? value.length>0 : typeof value==='string' && !!value.trim(); }
  function copy(value) { return Array.isArray(value) ? value.slice() : value; }
  function format(value) { return Array.isArray(value) ? value.join(', ') : value || ''; }
  function choiceIds(q) {
    var choices=q.choices || {};
    return Array.isArray(q.choiceOrder) ? q.choiceOrder.filter(function(id){return Object.prototype.hasOwnProperty.call(choices,id);}) : Object.keys(choices);
  }
  function check(q, answer) { var category=classify(q,answer);return category==='correct'?true:category==='wrong'?false:null; }
  root.MathPracticeAnswers = {check: check, classify: classify, formFeedback: formFeedback, enforceForm: enforceForm, gradingNotice: gradingNotice,
    responses:responses,same:same,hasAnswer:hasAnswer,copy:copy,format:format,choiceIds:choiceIds};
  if (typeof module !== 'undefined') module.exports = root.MathPracticeAnswers;
})(typeof window === 'undefined' ? globalThis : window);
