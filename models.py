from sqlmodel import SQLModel,Field,JSON,Column
from typing import List,Optional

class User(SQLModel,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    login:str=Field(nullable=False)
    password:str=Field(nullable=False)
    favourite_movies:List[int]=Field(sa_column=Column(JSON),default_factory=list)

  