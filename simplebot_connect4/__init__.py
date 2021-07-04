import os

import simplebot
from deltachat import Chat, Contact, Message
from pkg_resources import DistributionNotFound, get_distribution
from simplebot import DeltaBot
from simplebot.bot import Replies

from .connect4 import BLACK, WHITE, Board
from .orm import Game, init, session_scope

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    path = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(path):
        os.makedirs(path)
    path = os.path.join(path, "sqlite.db")
    init(f"sqlite:///{path}")


@simplebot.hookimpl
def deltabot_member_removed(bot: DeltaBot, chat: Chat, contact: Contact) -> None:
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=chat.id).first()
        if game:
            members = [contact.addr for contact in chat.get_contacts()]
            players = (bot.self_contact.addr, game.p1, game.p2)
            if any(map(lambda addr: addr not in members, players)):
                session.delete(game)
                if contact != bot.self_contact:
                    chat.remove_contact(bot.self_contact)


@simplebot.filter(name=__name__)
def filter_messages(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Process move coordinates in Connect4 game groups"""
    if message.text not in "1234567":
        return
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=message.chat.id).first()
        if game is None or game.board is None:
            return

        b = Board(game.board)
        player = (
            BLACK if game.black_player == message.get_sender_contact().addr else WHITE
        )
        if b.turn == player:
            if b.move(int(message.text)):
                game.board = b.export()
                replies.add(text=_run_turn(bot, game))
            else:
                replies.add(text="❌ Invalid move!", quote=message)


@simplebot.command
def c4_play(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Invite a friend to play Connect4.

    Example: /c4_play friend@example.com
    """
    if not payload or "@" not in payload:
        replies.add(
            text="❌ Invalid address. Example:\n/c4_play friend@example.com",
            quote=message,
        )
        return

    if payload == bot.self_contact.addr:
        replies.add(text="❌ Sorry, I don't want to play", quote=message)
        return

    sender = message.get_sender_contact().addr
    if sender == payload:
        replies.add(text="❌ You can't play with yourself", quote=message)
        return

    p1, p2 = sorted([sender, payload])
    with session_scope() as session:
        game = session.query(Game).filter_by(p1=p1, p2=p2).first()
        if game is None:  # first time playing with this contact
            p1_name = bot.get_contact(sender).name
            p2_name = bot.get_contact(payload).name
            chat = bot.create_group(f"4️⃣ {sender} 🆚 {payload}", [p1, p2])
            board = Board()
            game = Game(
                p1=p1, p2=p2, chat_id=chat.id, board=board.export(), black_player=sender
            )
            session.add(game)
            text = f"Hello {p2_name},\nYou have been invited by {p1_name} to play Connect4.\n\n{board.get_disc(BLACK)}: {p1_name}\n{board.get_disc(WHITE)}: {p2_name}\n\n"
            replies.add(text=text + _run_turn(bot, game), chat=chat)
        else:
            text = f"❌ You already have a game group with {payload}"
            replies.add(text=text, chat=bot.get_chat(game.chat_id))


@simplebot.command
def c4_surrender(message: Message, replies: Replies) -> None:
    """End the Connect4 game in the group it is sent."""
    sender = message.get_sender_contact()
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=message.chat.id).first()
        if game is None or sender.addr not in (game.p1, game.p2):
            replies.add(text="❌ This is not your game group", quote=message)
        elif game.board is None:
            replies.add(text="❌ There is no active game", quote=message)
        else:
            game.board = None
            if sender.addr == game.p1:
                game.p2_wins += 1
            else:
                game.p1_wins += 1
            replies.add(
                text=f"🏳️ Game Over.\n{sender.name} surrenders.\n\n▶️ Play again? /c4_new"
            )


@simplebot.command
def c4_score(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Get players score in the Connect4 game group where it is sent."""
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=message.chat.id).first()

        if game is None:
            replies.add(text="❌ This is not a Connect4 game group", quote=message)
        else:
            p1_name = bot.get_contact(game.p1).name
            p2_name = bot.get_contact(game.p2).name
            replies.add(
                text=f"📊 Score:\n{game.p1_wins} {p1_name}\n{game.p2_wins} {p2_name}"
            )


@simplebot.command
def c4_new(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Start a new Connect4 game in the current game group."""
    sender = message.get_sender_contact()
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=message.chat.id).first()
        if game is None or sender.addr not in (game.p1, game.p2):
            replies.add(text="❌ This is not your game group", quote=message)
        elif game.board is None:
            b = Board()
            game.board = b.export()
            game.black_player = sender.addr
            p2_name = bot.get_contact(
                game.p2 if sender.addr == game.p1 else game.p1
            ).name
            text = f"Game started!\n{b.get_disc(BLACK)}: {sender.name}\n{b.get_disc(WHITE)}: {p2_name}\n\n"
            replies.add(text=text + _run_turn(bot, game))
        else:
            replies.add(text="❌ There is an active game already", quote=message)


@simplebot.command
def c4_repeat(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send game board again."""
    with session_scope() as session:
        game = session.query(Game).filter_by(chat_id=message.chat.id).first()
        if not game:
            text = "❌ This is not a Connect4 game group"
        elif not game.board:
            text = "❌ There is no active game"
        else:
            text = _run_turn(bot, game)
        replies.add(text=text)


def _run_turn(bot: DeltaBot, game: Game) -> str:
    b = Board(game.board)
    result = b.result()
    if result is None:
        if b.turn == BLACK:
            turn = f"{b.get_disc(BLACK)} {bot.get_contact(game.black_player).name}"
        else:
            p2 = game.p2 if game.black_player == game.p1 else game.p1
            turn = f"{b.get_disc(WHITE)} {bot.get_contact(p2).name}"
        text = f"{turn} it's your turn...\n\n{b}"
    else:
        game.board = None
        if result == "-":
            text = "🤝 Game over.\nIt is a draw!"
        else:
            p1_name = bot.get_contact(game.p1).name
            p2_name = bot.get_contact(game.p2).name
            if result == BLACK:
                if game.black_player == game.p1:
                    game.p1_wins += 1
                    black_player = p1_name
                else:
                    game.p2_wins += 1
                    black_player = p2_name
                winner = f"{b.get_disc(BLACK)} {black_player}"
            else:
                if game.black_player != game.p1:
                    game.p1_wins += 1
                    white_player = p1_name
                else:
                    game.p2_wins += 1
                    white_player = p2_name
                winner = f"{b.get_disc(WHITE)} {white_player}"
            text = f"🏆 Game over.\n{winner} wins!\n\n📊 Score:\n{game.p1_wins} {p1_name}\n{game.p2_wins} {p2_name}\n\n{b}\n\n▶️ Play again? /c4_new"
    return text
