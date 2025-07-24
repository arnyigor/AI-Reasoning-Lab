# PuzzleDefinition.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
from ortools.sat.python import cp_model
from clue_types import ClueType # <<< ИМПОРТ

class PuzzleDefinition(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def generate_solution(self) -> pd.DataFrame: pass

    @abstractmethod
    def design_core_puzzle(self, solution: pd.DataFrame) -> Tuple[List[Tuple[ClueType, Any]], List[Tuple[ClueType, Any]]]: pass

    @abstractmethod
    def get_anchors(self, solution: pd.DataFrame) -> set: pass

    @abstractmethod
    def create_base_model_and_vars(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]: pass

    @abstractmethod
    def add_clue_constraint(self, model: cp_model.CpModel, variables: Dict[str, Any], clue: Tuple[ClueType, Any]): pass

    @abstractmethod
    def format_clue(self, clue: Tuple[ClueType, Any]) -> str: pass

    @abstractmethod
    def quality_audit_and_select_question(self, puzzle: List[Tuple[ClueType, Any]], solution: pd.DataFrame) -> Tuple[List, Optional[Dict]]: pass

    @abstractmethod
    def print_puzzle(self, final_clues: List[Tuple[ClueType, Any]], question_data: Dict[str, str], solution: pd.DataFrame): pass