from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase):
    """SQLAlchemy 2.0スタイルのベースクラス

    MappedAsDataclassにより、型付きの__init__が自動生成される
    """

    pass
