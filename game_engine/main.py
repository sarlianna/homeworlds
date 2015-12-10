"""Module creating the main game loop and handling input.
"""
#TODO: whole file is really ugly -- redo to compose functions instead of this
#      nasty imperative nested function stuff, wtf is that.
#      hard as fuck to maintain is what it is

from importlib import (
    import_module
)
import random
import sys

from py_types.runtime import (
    schema,
    SchemaOr,
    typecheck,
)

from game import (
    GAMESTATE,
    ACTION_METHODS,
    ACTION_VALIDATORS,

)


BOT_PATH = "bots."
LOG_FILE = "last_game.log"
DEBUG = False


@schema
def check_player_lost(game: GAMESTATE) -> SchemaOr(type(None), [int]):
    """Returns a list of players who have lost, or None."""
    players_with_homeworlds = []
    for _, system in game["systems"].items():
        if system["star"]["owner"] in game["players"]:
            owned_ships = [ship for ship in system["ships"] if ship["owner"] == system["star"]["owner"]]
            if owned_ships:
                players_with_homeworlds.append(system["star"]["owner"])

    players_without = [pl for pl in game["players"] if pl not in players_with_homeworlds]
    if players_without:
        return players_without
    else:
        return None


@schema
def interpret_bot_input(game: GAMESTATE, bot_input: list) -> SchemaOr((bool, str), (bool, GAMESTATE)):
    """Takes bot input and calls the appropriate methods.
    Bots are expected to return a list in this format:
    ["action", (args)]
    where "action" corresponds to a key in ACTION_METHODS
    and args is the appropriate arguments for that method.
    """

    for index, _ in enumerate(bot_input):
        if index % 2 != 0:
            continue
        action = bot_input[index]
        args = bot_input[index + 1]
        validator = ACTION_VALIDATORS[action]
        method = ACTION_METHODS[action]

        print(validator)
        print(args)
        is_valid = validator(game, args)
        if not is_valid[0]:
            return is_valid
        game = method(game, *args)

    return (True, game)


def next_player(player: int) -> int:
    """Super hacky, only works for 2-player where ids are 1 and 2,
    doesn't even look at gamestate to see what ids there are.
    """
    if player == 1:
        return 2
    else:
        return 1


@typecheck
def main(first_bot: str, second_bot: str) -> type(None):
    """Instantiates game state, loops on bot input.
    won Ugliest Thing Award in 2015

    Bots are expected to be a module string with a function "take_turn"
    present.
    expected signature:
    take_turn(game: GAMESTATE, message: str) -> GAMESTATE:

    message will contain an error message on the previous input, if any.
    """
    player_one = import_module(BOT_PATH + first_bot)
    player_one_turn = player_one.take_turn

    player_two = import_module(BOT_PATH + second_bot)
    player_two_turn = player_two.take_turn

    player_calls = {1: player_one_turn, 2: player_two_turn}

    gamestate = {
        "reserve": {
            "g1": 3,
            "g2": 3,
            "g3": 3,
            "b1": 3,
            "b2": 3,
            "b3": 3,
            "y1": 3,
            "y2": 3,
            "y3": 3,
            "r1": 3,
            "r2": 3,
            "r3": 3
        },
        "systems": {},
        "players": [1, 2],
        "current_player": 1,
        "history": [],
        "system_count": 0,
        "owner_count": 2
    }

    # random player goes first
    gamestate["current_player"] = random.choice(gamestate["players"])

    turn_count = 0
    while True:
        turn = player_calls[gamestate["current_player"]](gamestate, "")
        result = interpret_bot_input(gamestate, turn)
        while not result[0]:
            turn = player_calls[gamestate["current_player"]](gamestate, result[1])
            result = interpret_bot_input(gamestate, turn)

        gamestate = result[1]
        turn_summary = ["p{}".format(gamestate["current_player"])]
        turn_summary.append(turn)
        gamestate["history"].append(turn_summary)

        if DEBUG:
            print(turn_summary)
            print(gamestate)

        turn_count += 1
        # don't check for lose conditions on setup turns
        if turn_count > 2:
            losers = check_player_lost(gamestate)
            if losers:
                gamestate["history"].append(["END", "players {} have lost".format(losers)])
                print("GAME END - these players have lost: {}".format(losers))
                break

        gamestate["current_player"] = next_player(gamestate["current_player"])

    with open(LOG_FILE, "w+") as log:
        log.write(str(gamestate["history"]).replace("], ", "],\n"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
