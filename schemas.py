from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentValidation(BaseModel):
    is_valid: bool = Field(description="True if document qualifies as target type, False otherwise.")
    doc_type: str = Field(description="'resume', 'job_description', or 'invalid'")
    reason: str = Field(description="Brief explanation of the validation result.")

class CourseItem(BaseModel):
    skill: str
    course_name: str
    platform: str
    url: str

class CandidateEvaluation(BaseModel):
    filename: str
    candidate_name: str = "Candidate"
    is_valid_resume: bool = True
    rejection_reason: Optional[str] = None
    overall_score: int = Field(default=0, ge=0, le=100)
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    recommended_courses: List[CourseItem] = []

class BatchEvaluationResponse(BaseModel):
    is_valid_jd: bool
    jd_rejection_reason: Optional[str] = None
    results: List[CandidateEvaluation] = []