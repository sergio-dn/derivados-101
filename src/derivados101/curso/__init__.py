"""Temas de derivados USD/CLP, uno por pregunta, en orden de lectura (contenido puro, sin Streamlit)."""

from .cap1 import CHAPTER as CAP1
from .cap2 import CHAPTER as CAP2
from .cap3 import CHAPTER as CAP3
from .cap3b import CHAPTER as CAP3B
from .cap3c import CHAPTER as CAP3C
from .cap4 import CHAPTER as CAP4
from .cap4b import CHAPTER as CAP4B
from .cap5 import CHAPTER as CAP5
from .cap6 import CHAPTER as CAP6
from .model import Chapter, Chart, Choice, Concept, Demo, Example, Numeric, Screen, Summary

CHAPTERS: list[Chapter] = [CAP1, CAP2, CAP3, CAP3B, CAP3C, CAP4, CAP4B, CAP5, CAP6]

__all__ = ["CHAPTERS", "Chapter", "Chart", "Choice", "Concept", "Demo", "Example", "Numeric", "Screen", "Summary"]
