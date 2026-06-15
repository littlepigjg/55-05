import re
import jieba
from whoosh.analysis import Analyzer, Token
from whoosh.analysis.filters import LowercaseFilter, StopFilter


class ChineseTokenizer:
    def __init__(self):
        jieba.setLogLevel(60)
        self._punct_re = re.compile(r"[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+")

    def __call__(self, value, positions=False, chars=False, keeporiginal=False,
                 removestops=True, start_pos=0, start_char=0, mode='', **kwargs):
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")

        text = self._punct_re.sub(" ", value)
        words = jieba.lcut(text, cut_all=False)

        pos = start_pos
        char_pos = start_char

        for word in words:
            word = word.strip()
            if not word:
                continue

            token = Token()
            token.text = word
            token.original = value if keeporiginal else None

            if positions:
                token.pos = pos
                pos += 1

            if chars:
                token.startchar = char_pos
                token.endchar = char_pos + len(word)
                char_pos += len(word)

            token.mode = mode
            yield token


class ChineseAnalyzer(Analyzer):
    def __init__(self, stoplist=None):
        self._tokenizer = ChineseTokenizer()
        self._filters = [
            LowercaseFilter(),
        ]
        if stoplist:
            self._filters.append(StopFilter(stoplist=stoplist))

    def __call__(self, value, **kwargs):
        tokens = self._tokenizer(value, **kwargs)
        for f in self._filters:
            tokens = f(tokens)
        return tokens


def chinese_analyzer():
    return ChineseAnalyzer()
