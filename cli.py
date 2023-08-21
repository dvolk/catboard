import argh

from app import app, db, User, Board


def list_users():
    with app.app_context():
        for u in User.query.all():
            print(f"{u.id}. {u.username}")


def list_boards():
    with app.app_context():
        for b in Board.query.all():
            print(f"{b.id}. {b.name}")


def add_user(username, password):
    with app.app_context():
        u = User(username=username, password_hash="")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()


def remove_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def set_password(username, new_password):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def user_add_board(username, board_id):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            board = Board.query.filter_by(id=board_id).first()
            user.boards.append(board)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def user_remove_board(username, board_id):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            board = Board.query.filter_by(id=board_id).first()
            if board in user.boards:
                user.boards.remove(board)
                db.session.commit()
            else:
                print(f"No board found with name: {board_id}")
        else:
            print(f"No user found with username: {username}")


if __name__ == "__main__":
    argh.dispatch_commands(
        [
            list_users,
            list_boards,
            add_user,
            remove_user,
            set_password,
            user_add_board,
            user_remove_board,
        ]
    )
