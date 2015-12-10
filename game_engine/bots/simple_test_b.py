from py_types.runtime import (
    schema,
)

from game import (
    GAMESTATE,
    SYSTEM,
    Color,
)


MOVE_LIST = [
    ["setup", ([{"color": "blue", "size":1}, {"color": "yellow", "size": 2}], {"color": "green", "size": 3})],
]
turn_count = -1


@schema
def count_color_in_system(system: SYSTEM, color: Color) -> int:
    count = 0
    for ship in system["ships"]:
        if ship["piece"]["color"] == color:
            count += 1

    for piece in system["star"]["pieces"]:
        if piece["color"] == color:
            count += 1

    return count


@schema
def take_turn(game: GAMESTATE, message: str) -> list:
    if message:
        raise ValueError(message)

    global turn_count
    turn_count += 1

    if turn_count >= 1:
        global homeworld_id
        systems = [(sid, sys) for sid, sys in game["systems"].items() if sys["star"]["owner"] == game["current_player"]]
        homeworld_id = systems[0][0]

    try:
        move = MOVE_LIST[turn_count]
    except:
        move = None
        other_systems = [(sid, sys) for sid, sys in game["systems"].items() if sys["star"]["owner"] == game["current_player"]]
        for sid, sys in other_systems:
            if count_color_in_system(sys, "green") > 3:
                move = ["catastrophe", (sid, "green")]

        if move is None:
            move = ["construct", (homeworld_id, "green")]

    return move
