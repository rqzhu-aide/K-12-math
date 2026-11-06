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
    var source=q.gradingStatus==='disputed'?q:q.knowledgeGraph;
    return source && source.gradingStatus==='disputed'
      ? source.gradingNote || 'This problem is available for study without grading.' : null;
  }
  function classify(q, answer) {
    if (gradingNotice(q)!==null) return 'not_graded';
    if ((q.rejectedAnswers || []).some(function(x){return normal(x)===normal(answer);})) return 'wrong';
    var kind = q.responseType || 'choice';
    if (kind === 'choice') return answer === q.answer ? 'correct' : 'wrong';
    if (kind === 'self') return null;
    if (kind === 'short') {
      var accepted=[q.answer].concat(q.acceptedAnswers || []);
      if (accepted.some(function(x){return normal(x)===normal(answer);})) return enforceForm(q,answer,'correct');
      if (q.answerForm==='standard-monomial') {
        var withoutSigns=formText(answer).replace(/\*|·|×|\\times|\\cdot/g,'');
        if (accepted.some(function(x){return formText(x)===withoutSigns;})) return formFeedback(q,answer)?'partial':'correct';
      }
      return null;
    }
    if (kind !== 'numeric') return null;
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
  function check(q, answer) { var category=classify(q,answer);return category==='correct'?true:category==='wrong'?false:null; }
  root.MathPracticeAnswers = {check: check, classify: classify, formFeedback: formFeedback, enforceForm: enforceForm, gradingNotice: gradingNotice};
  if (typeof module !== 'undefined') module.exports = root.MathPracticeAnswers;
})(typeof window === 'undefined' ? globalThis : window);
