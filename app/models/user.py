"""User model for authentication."""

from flask_login import UserMixin

# Temporary in-memory storage for users (no database yet)
_users = {}


class User(UserMixin):
    """
    User model for Google OAuth authentication.

    Uses Flask-Login's UserMixin for session management. Users are
    stored in memory (_users dict) so they persist during the session.
    """

    def __init__(
        self,
        id_: str,
        email: str,
        name: str,
        picture: str = None,
    ):
        self.id = id_
        self.email = email
        self.name = name
        self.picture = picture

    @staticmethod
    def get(user_id: str):
        """
        Get a user by ID.

        Retrieves from in-memory storage.
        TODO: Implement database lookup when database is added.
        """
        return _users.get(user_id)

    @staticmethod
    def create(id_: str, email: str, name: str, picture: str = None):
        """
        Create a new user.

        Stores in memory.
        TODO: Implement database persistence when database is added.
        """
        user = User(id_=id_, email=email, name=name, picture=picture)
        # Store in memory
        _users[id_] = user
        return user

    def __repr__(self):
        return f"<User {self.email}>"
