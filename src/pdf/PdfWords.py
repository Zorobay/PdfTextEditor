import typing
import uuid

from src.pdf.PdfWord import PdfWord


class PdfWords:

    def __init__(self, words: list[PdfWord] = None):
        self._words: list[PdfWord] = []
        self._word_index_map: dict[uuid.UUID, int] = dict()
        self.set_words(words)
        
    def __iter__(self) -> typing.Iterator:
        return iter(self._words)

    def size(self) -> int:
        return len(self._words)

    def set_words(self, words: list[PdfWord]):
        if words:
            self._words = words
            self._word_index_map = {w.uuid: i for i, w in enumerate(words)}

    def add(self, word: PdfWord) -> None:
        self._words.append(word)
        self._word_index_map[word.uuid] = len(self._words) - 1

    def clear(self) -> None:
        self._words = []
        self._word_index_map = dict()

    def get_index(self, word_id: uuid.UUID) -> int:
        return self._word_index_map[word_id]

    def get(self, index: int) -> PdfWord:
        return self._words[index]
    
    def get_by_id(self, word_id: uuid.UUID) -> PdfWord:
        return self._words[self.get_index(word_id)]
