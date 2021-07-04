class TestPlugin:
    def test_play(self, mocker) -> None:
        sender = "sender1@example.org"
        receiver = "friend1@example.org"

        # error: missing address
        msg = mocker.get_one_reply("/c4_play", addr=sender)
        assert "❌" in msg.text

        # error: can't play against bot
        msg = mocker.get_one_reply(
            f"/c4_play {mocker.bot.self_contact.addr}", addr=sender
        )
        assert "❌" in msg.text

        # error: can't play against yourself
        msg = mocker.get_one_reply(f"/c4_play {sender}", addr=sender)
        assert "❌" in msg.text

        # create game group
        msg = mocker.get_one_reply(f"/c4_play {receiver}", addr=sender)
        assert "❌" not in msg.text
        assert msg.chat.is_group()

        game_group = msg.chat

        # error: already have a game group with that player
        msg = mocker.get_one_reply(f"/c4_play {sender}", addr=receiver)
        assert "❌" in msg.text
        assert msg.chat == game_group

    def test_new(self, mocker) -> None:
        # error: not a game group
        msg = mocker.get_one_reply("/c4_new", group="group1")
        assert "❌" in msg.text

        # create game group
        msg = mocker.get_one_reply("/c4_play invited_player@example.org")
        assert msg.chat.is_group()
        game_group = msg.chat

        # error: there is an active game
        msg = mocker.get_one_reply("/c4_new", group=game_group)
        assert "❌" in msg.text

        # end current game
        msg = mocker.get_one_reply("/c4_surrender", group=game_group)
        assert "❌" not in msg.text

        # error: sender is not a player
        msg = mocker.get_one_reply(
            "/c4_new", addr="nonPlayer@example.org", group=game_group
        )
        assert "❌" in msg.text

        # start a new game
        msg = mocker.get_one_reply("/c4_new", group=game_group)
        assert "❌" not in msg.text
        assert msg.chat == game_group

    def test_repeat(self, mocker) -> None:
        # error: not a game group
        msg = mocker.get_one_reply("/c4_repeat", group="group1")
        assert "❌" in msg.text

        # create game group
        msg = mocker.get_one_reply("/c4_play invited_player@example.org")
        assert msg.chat.is_group()
        game_group = msg.chat

        # repeat board
        msg = mocker.get_one_reply("/c4_repeat", group=game_group)
        assert "❌" not in msg.text

        # end current game
        msg = mocker.get_one_reply("/c4_surrender", group=game_group)
        assert "❌" not in msg.text

        # error: there is no active game
        msg = mocker.get_one_reply("/c4_repeat", group=game_group)
        assert "❌" in msg.text

    def test_score(self, mocker) -> None:
        # error: not a game group
        msg = mocker.get_one_reply("/c4_score", group="group1")
        assert "❌" in msg.text

        # create game group
        msg = mocker.get_one_reply("/c4_play invited_player@example.org")
        assert msg.chat.is_group()
        game_group = msg.chat

        # get score
        msg = mocker.get_one_reply("/c4_score", group=game_group)
        assert "❌" not in msg.text

    def test_surrender(self, mocker) -> None:
        # error: not a game group
        msg = mocker.get_one_reply("/c4_surrender", group="group1")
        assert "❌" in msg.text

        # create game group
        msg = mocker.get_one_reply("/c4_play invited_player@example.org")
        assert msg.chat.is_group()
        game_group = msg.chat

        # error: sender is not a player
        msg = mocker.get_one_reply(
            "/c4_surrender", addr="nonPlayer@example.org", group=game_group
        )
        assert "❌" in msg.text

        # end current game
        msg = mocker.get_one_reply("/c4_surrender", group=game_group)
        assert "❌" not in msg.text

        # error: there is no active game
        msg = mocker.get_one_reply("/c4_surrender", group=game_group)
        assert "❌" in msg.text

    def test_filter(self, mocker) -> None:
        player2 = "invited_player@example.org"

        # not a game group
        msgs = mocker.get_replies("1", group="group1")
        assert not msgs

        # create game group
        msg = mocker.get_one_reply(f"/c4_play {player2}")
        assert msg.chat.is_group()
        game_group = msg.chat

        # it isn't player2's turn
        msgs = mocker.get_replies("1", addr=player2, group=game_group)
        assert not msgs

        # invalid move, ignored
        msgs = mocker.get_replies("8", group=game_group)
        assert not msgs

        # player1 plays in column 1
        msg = mocker.get_one_reply("1", group=game_group)
        assert "❌" not in msg.text

        # player2 plays in column 1
        msg = mocker.get_one_reply("1", addr=player2, group=game_group)
        assert "❌" not in msg.text

        # fill column 1
        mocker.get_one_reply("1", group=game_group)
        mocker.get_one_reply("1", addr=player2, group=game_group)
        mocker.get_one_reply("1", group=game_group)
        mocker.get_one_reply("1", addr=player2, group=game_group)

        # error: invalid move, column 1 is full
        msg = mocker.get_one_reply("1", group=game_group)
        assert "❌" in msg.text

        # make player1 win
        msg = mocker.get_one_reply("2", group=game_group)
        assert "❌" not in msg.text and "🏆" not in msg.text
        mocker.get_one_reply("2", addr=player2, group=game_group)
        mocker.get_one_reply("3", group=game_group)
        mocker.get_one_reply("3", addr=player2, group=game_group)
        msg = mocker.get_one_reply("4", group=game_group)
        assert "🏆" in msg.text

        # no active game, ignored
        msgs = mocker.get_replies("2", addr=player2, group=game_group)
        assert not msgs
