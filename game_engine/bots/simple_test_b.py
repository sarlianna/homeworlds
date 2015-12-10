from py_types.runtime import (
    schema,
    SchemaOr,
)

from game import (
    GAMESTATE,
    SYSTEM,
    PIECE,
    Color,
    check_color_in_reserve,
    check_piece_in_reserve,
)


turn_count = -1
ship_count = 0


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
def get_piece_from_key(key: str) -> PIECE:
    letter = {
        "g": "green",
        "y": "yellow",
        "b": "blue",
        "r": "red"
    }
    return {"color": letter[key[0]], "size": int(key[1])}


@schema
def get_neutral_system_of_size(game: GAMESTATE, size: int) -> SchemaOr(type(None), (int, SYSTEM)):
    for key, value in game["systems"].items():
        if value["star"]["owner"] == 0 and value["star"]["pieces"][0]["size"] == size:
            return (key, value)

    return None


@schema
def take_turn(game: GAMESTATE, message: str) -> list:
    if message:
        raise ValueError(message)

    global turn_count
    turn_count += 1

    if turn_count == 1:
        global homeworld_id
        systems = [(sid, sys) for sid, sys in game["systems"].items() if sys["star"]["owner"] == game["current_player"]]
        homeworld_id = systems[0][0]

    move = []
    if turn_count == 0:
        move = ["setup", ([{"color": "blue", "size":1}, {"color": "yellow", "size": 3}], {"color": "green", "size": 3})]
    elif turn_count >= 1 and turn_count < 31:
        other_systems = [(sid, sys) for sid, sys in game["systems"].items() if sys["star"]["owner"] != game["current_player"]]
        for sid, sys in other_systems:
            if count_color_in_system(sys, "green") > 3:
                move += ["catastrophe", (sid, "green")]

        ships_at_homeworld = [ship for ship in game["systems"][homeworld_id]["ships"] if ship["owner"] == game["current_player"]]
        color_ships_at_hw = [ship["piece"]["color"] for ship in ships_at_homeworld]
        if len(ships_at_homeworld) > 2:
            if ship_count > 4:
                # get first available piece
                new_system_piece = None
                # get first available piece
                new_system_piece = None
                for key, value in game["reserve"].items():
                    if value > 0 and key[1] == '2':
                        new_system_piece = get_piece_from_key(key)
                        break
                move += ["move", (homeworld_id, ships_at_homeworld[-1], {"new_piece": new_system_piece})]


        else:
            for color in ["green", "yellow", "red", "blue"]:
                if check_color_in_reserve(game, color)[0]:
                    if color in color_ships_at_hw:
                        move += ["construct", (homeworld_id, color)]
                        global ship_count
                        ship_count += 1
                    else:
                        for ship in ships_at_homeworld:
                            if check_piece_in_reserve(game, {"color": color, "size": ship["piece"]["size"]}):
                                move += ["trade", (homeworld_id, ships_at_homeworld[-1], color)]
                                break
                    break

    elif not move or turn_count > 30:
        print("attempting to suicide")
        ships_at_homeworld = [ship for ship in game["systems"][homeworld_id]["ships"] if ship["owner"] == game["current_player"]]
        print("ships remaining at homeworld: {}".format(len(ships_at_homeworld)))
        neutral_system_id = get_neutral_system_of_size(game, 3)[0]
        move = ["move", (homeworld_id, ships_at_homeworld[-1], neutral_system_id)]

    print(turn_count)
    return move
