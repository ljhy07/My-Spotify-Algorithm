from typing import List, Optional
from sqlmodel import SQLModel, Field

class SearchData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    searchValue: str
