from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime

class PuzzleClue(BaseModel):
    id: str
    text: str
    category: str
    difficulty: str
    hint: Optional[str] = None

class PuzzleGrid(BaseModel):
    size: int  # 4x4, 5x5, etc.
    categories: List[str]
    items: List[str]
    grid_data: Dict[str, Dict[str, str]]  # category -> item -> value

class GrandmasterPuzzle(BaseModel):
    id: str
    name: str
    theme: str
    difficulty: str
    grid: PuzzleGrid
    clues: List[PuzzleClue]
    solution: Dict[str, str]  # item -> position mapping
    story: str
    created_at: datetime
    tags: List[str] = []

class PuzzleAttempt(BaseModel):
    puzzle_id: str
    session_id: str
    user_solution: Dict[str, str]
    is_correct: bool
    time_taken: float
    hints_used: int
    attempts: int
    timestamp: datetime

class PuzzleResult(BaseModel):
    puzzle_id: str
    session_id: str
    model_name: str
    success: bool
    accuracy: float
    reasoning_steps: List[str]
    final_answer: Dict[str, str]
    confidence_score: Optional[float]
    execution_time: float
    error_message: Optional[str]
    timestamp: datetime

class JudgeConfiguration(BaseModel):
    id: str
    name: str
    model_name: str
    temperature: float = 0.3
    system_prompt: str
    evaluation_criteria: List[str]
    bias_checks: List[str] = []
    calibration_data: Dict[str, Any] = {}

class JudgeResult(BaseModel):
    judge_id: str
    session_id: str
    test_id: str
    model_name: str
    score: float
    reasoning: str
    criteria_scores: Dict[str, float]
    bias_detected: bool
    confidence: float
    timestamp: datetime

class JudgeComparison(BaseModel):
    test_id: str
    model_name: str
    judge_results: List[JudgeResult]
    consensus_score: float
    disagreement_level: float
    recommended_score: float

class GrandmasterAnalytics(BaseModel):
    total_puzzles: int
    solved_puzzles: int
    average_difficulty: str
    success_rate_by_difficulty: Dict[str, float]
    common_mistakes: List[Dict[str, Any]]
    performance_trends: List[Dict[str, Any]]

class JudgeAnalytics(BaseModel):
    judge_id: str
    total_evaluations: int
    average_score: float
    consistency_score: float
    bias_incidents: int
    calibration_accuracy: float
    performance_over_time: List[Dict[str, Any]]