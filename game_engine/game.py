"""Module implementing main game logic."""

from operator import (
    add,
)
from functools import (
    reduce,
)

from py_types.runtime import (
    schema,
    SchemaOr,
    typecheck,
)
from py_types.type_defs import (
    ValidatedType,
    TypedDict,
)

##################
# Types / Schemas
##################

#TODO: move owner out of star and into system

@typecheck
def check_color(color: str) -> bool:
    return color in ("red", "green", "blue", "yellow")

class Color(metaclass=ValidatedType):
    type_members = [str]
    validators = [check_color]


@typecheck
def check_size(size: int) -> bool:
    return size in (1, 2, 3)

class Size(metaclass=ValidatedType):
    type_members = [int]
    validators = [check_size]


@typecheck
def check_action(action: str) -> bool:
    return action in ("construct",
                      "move",
                      "trade",
                      "attack",
                      "sacrifice",
                      "catastrophe")

class Action(metaclass=ValidatedType):
    type_members = [str]
    validators = [check_action]


OwnerId = int
NO_OWNER = 0

PIECE = {
    "color": Color,
    "size": Size
}

NEW_SYSTEM = {
    "new_piece": PIECE
}
ExistingSystemId = int
SystemId = SchemaOr(int, NEW_SYSTEM)

SHIP = {
    "owner": OwnerId,
    "piece": PIECE
}
STAR = {
    "owner": OwnerId,
    "pieces": [PIECE]
}
SYSTEM = {
    "star": STAR,
    "ships": [SHIP]
}
# type_key, quantity
RESERVE = {
    "g1": int,
    "g2": int,
    "g3": int,
    "b1": int,
    "b2": int,
    "b3": int,
    "y1": int,
    "y2": int,
    "y3": int,
    "r1": int,
    "r2": int,
    "r3": int
}

ACTION_ARGS = [SchemaOr(int, str, dict)]
EVENT = [str, str, (ACTION_ARGS)]

GAMESTATE = {
    "reserve": RESERVE,
    #TODO: "systems": TypedDict(ExistingSystemId, SYSTEM),
    "systems": dict,
    "players": [OwnerId],
    "current_player": OwnerId,
    "history": [EVENT],
    "system_count": int,
    "owner_count": int
}

CONSTRUCT_ARGS = [ExistingSystemId, Color]
# from, ship, to
MOVE_ARGS = [ExistingSystemId, SHIP, SystemId]
TRADE_ARGS = [ExistingSystemId, SHIP, Color]
ATTACK_ARGS = [ExistingSystemId, SHIP]
SACRIFICE_ARGS = [ExistingSystemId, SHIP, [(Action, ACTION_ARGS)]]
CATASTROPHE_ARGS = [ExistingSystemId, Color]
SETUP_ARGS = [[PIECE], PIECE]


###################
# Utility methods
# These should be exposed to bots/clients also
###################

COLOR_ACTIONS = {
    "green": "construct",
    "yellow": "move",
    "blue": "trade",
    "red": "attack"
}


@schema
def check_player_has_ship(game: GAMESTATE, system_id: int, player_ship: SHIP) -> (bool, str):
    """Returns (True, "") if player_id has ship in system_id, else (False, message)"""
    if not validate_player_id(game, player_ship["owner"]):
        return (False, "Player id {} is not valid.".format(player_ship["owner"]))
    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))

    ship_pieces_in_system = [ship["piece"] for ship in game["systems"][system_id]["ships"] if ship["owner"] == player_ship["owner"]]
    for piece in ship_pieces_in_system:
        if piece["color"] == player_ship["piece"]["color"] and piece["size"] == player_ship["piece"]["size"]:
            return (True, "")

    return (False, "Ship {} owned by {} not found in system.".format(player_ship, player_ship["owner"]))


@schema
def check_piece_in_reserve(game: GAMESTATE, piece: PIECE) -> bool:
    """Checks if a piece with identical attributes to given piece exists in reserve"""
    piece_key = piece["color"][0] + str(piece["size"])
    if game["reserve"][piece_key] > 0:
        return True
    else:
        return False


@schema
def check_color_in_reserve(game: GAMESTATE, color: Color) -> (bool, str):
    """Check if the bank/reserve has pieces of a particular color and any size."""
    color_key = color[0]
    keys = [color_key + str(num) for num in range(1, 4)]
    sum_pieces = reduce(add, [game["reserve"][key] for key in keys])
    if sum_pieces > 0:
        return (True, "")
    else:
        return (False, "Insufficient {} pieces.".format(color))


@schema
def get_colors_in_system(game: GAMESTATE, system: SystemId) -> [Color]:
    """Get colors in system present on any ships and any stars."""
    all_ship_colors = [ship["piece"]["color"] for ship in game["systems"][system]["ships"]]
    all_star_colors = [piece["color"] for piece in game["systems"][system]["star"]["pieces"]]
    return set(all_ship_colors + all_star_colors)


@schema
def get_colors_in_system_for_player(game: GAMESTATE, player: OwnerId, system: SystemId) -> [Color]:
    """Get colors in system present on ships a player owns.  Does not include stars."""
    all_colors = {ship["piece"]["color"] for ship in game["systems"][system]["ships"] if ship["owner"] == player}
    return list(all_colors)


@schema
def get_ships_in_system(game: GAMESTATE, system: SystemId) -> [SHIP]:
    all_ships = [ship for ship in game["systems"][system]["ships"]]
    return all_ships


@schema
def get_ships_in_system_for_player(game: GAMESTATE, player: OwnerId, system: SystemId) -> [SHIP]:
    all_ships = [ship for ship in game["systems"][system]["ships"] if ship["owner"] == player]
    return all_ships


@schema
def create_piece_key(piece: PIECE) -> str:
    return piece["color"][0] + str(piece["size"])

###################
# Validation methods
###################

#TODO: move some of this logic to types maybe?


@schema
def validate_player_id(game: GAMESTATE, player_id: int) -> bool:
    """Returns True if the player_id is a valid OwnerId"""
    return player_id in game["players"]


@schema
def validate_system_id(game: GAMESTATE, system_id: int) -> bool:
    """Returns True if the system_id is a valid SystemId"""
    return system_id in game["systems"].keys()


@schema
def validate_construct(game: GAMESTATE, args: CONSTRUCT_ARGS, sacrifice: bool=False) -> (bool, str):
    """Returns (True, "") if the construct is legal, (False, message) otherwise.
    CONSTRUCT_ARGS = [SystemId, Color]
    """
    system_id = args[0]
    color = args[1]

    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))
    if not check_color_in_reserve(game, color)[0]:
        return (False, "Not enough pieces of color {} in reserve.".format(color))

    colors_in_system = get_colors_in_system(game, system_id)
    owned_colors_in_system = get_colors_in_system_for_player(game, game["current_player"], system_id)
    if color not in owned_colors_in_system:
        return (False, "Current player does not own a ship of color {} in system {}.".format(color, system_id))

    if not sacrifice and "green" not in colors_in_system:
        return (False, "There is no green ability in system {}.".format(system_id))

    return (True, "")


@schema
def validate_move(game: GAMESTATE, args: MOVE_ARGS, sacrifice: bool=False) -> (bool, str):
    """Returns (True, "") if the move is legal, (False, message) otherwise.
    # from, ship, to
    MOVE_ARGS = [SystemId, SHIP, SystemId]
    """
    from_system_id = args[0]
    ship = args[1]
    to_system_id = args[1]

    if not validate_system_id(game, from_system_id):
        return (False, "System id {} is not valid.".format(from_system_id))
    if isinstance(to_system_id, int) and not validate_system_id(game, to_system_id):
        return (False, "System id {} is not valid.".format(to_system_id))
    elif isinstance(to_system_id, dict) and not check_piece_in_reserve(game, to_system_id["piece"]):
        return (False, "Not enough pieces in reserve to create specified system: {}".format(to_system_id))
    if ship[0] != game["current_player"]:
        return (False, "Current player does not own given ship.")

    if not check_player_has_ship(game, from_system_id, ship):
        return (False, "Current player does not have a ship of given piece in system {}.".format(from_system_id))

    from_system = game["systems"][from_system_id]
    to_system = game["systems"][to_system_id]

    from_star_sizes = {star["size"] for star in from_system["star"]["pieces"]}
    to_star_sizes = {star["size"] for star in to_system["star"]["pieces"]}
    if len(from_star_sizes.intersect(to_star_sizes)) > 0:
        return (False, "Target system {} has a star of the same size as origin system {}.".format(to_system_id, from_system_id))

    colors_in_system = get_colors_in_system(game, from_system_id)
    if not sacrifice and "yellow" not in colors_in_system:
        return (False, "There is no yellow ability in system {}.".format(from_system_id))

    return (True, "")


@schema
def validate_trade(game: GAMESTATE, args: TRADE_ARGS, sacrifice: bool=False) -> (bool, str):
    """Returns (True, "") if the trade is legal, (False, message) otherwise.
    TRADE_ARGS = [SystemId, SHIP, Color]
    """
    system_id = args[0]
    ship = args[1]
    color = args[2]

    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))

    new_piece = [color, ship["piece"]["size"]]
    if not check_piece_in_reserve(game, new_piece):
        return (False, "No pieces in reserve to trade with.")

    colors_in_system = get_colors_in_system(game, system_id)
    if not sacrifice and "blue" not in colors_in_system:
        return (False, "There is no blue ability in system {}.".format(system_id))

    return (True, "")


@schema
def validate_attack(game: GAMESTATE, args: ATTACK_ARGS, sacrifice: bool=False) -> (bool, str):
    """Returns (True, "") if the attack is legal, (False, message) otherwise.
    ATTACK_ARGS = [SystemId, SHIP]
    """
    system_id = args[0]
    ship = args[1]

    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))
    if ship[0] == game["current_player"]:
        return (False, "Current player already owns target ship.")

    target_size = ship["piece"]["size"]
    player_ships = get_ships_in_system_for_player(game, game["current_player"], system_id)
    is_larger_size = {_ship["piece"]["size"] >= target_size for _ship in player_ships}
    if not any(list(is_larger_size)):
        return (False, "Current player does not have a ship large enough to attack target ship.")

    colors_in_system = get_colors_in_system(game, system_id)
    if not sacrifice and "red" not in colors_in_system:
        return (False, "There is no red ability in system {}.".format(system_id))

    return (True, "")


@schema
def validate_sacrifice(game: GAMESTATE, args: SACRIFICE_ARGS) -> (bool, str):
    """Returns (True, "") if the sacrifice is legal, (False, message) otherwise.
    SACRIFICE_ARGS = [SystemId, SHIP, [(str, ACTION_ARGS)]]
    """
    system_id = args[0]
    ship = args[1]
    subsequent_actions = args[2]

    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))
    if not check_player_has_ship(game, system_id, ship):
        return (False, "Current player does not have a ship of given piece in system {}.".format(system_id))

    valid_action_types = [COLOR_ACTIONS[ship["piece"]["color"]], "catastrophe"]
    available_action_count = ship["piece"]["size"]
    action_count = len([a[0] for a in subsequent_actions if a[0] != "catastrophe"])
    if action_count != available_action_count:
        return (False, "Number of subsequent actions does not match the size of the sacrificed ship. " +
                       "Expected: {}, Given: {}".format(available_action_count, action_count))

    for action_args in subsequent_actions:
        action, a_args = action_args
        # tell action checks this is a sacrifice action
        a_args += [True]
        if action not in valid_action_types:
            return (False, "Given action {} is not valid, expected one of {}.".format(action, valid_action_types))

        action_validation = ACTION_VALIDATORS[action](a_args)
        if not action_validation[0]:
            return (False, "Action {} with args {} is not valid: {}".format(action, a_args, action_validation[1]))

    return (True, "")


@schema
def validate_catastrophe(game: GAMESTATE, args: CATASTROPHE_ARGS) -> (bool, str):
    """Returns (True, "") if the sacrifice is legal, (False, message) otherwise.
    CATASTROPHE_ARGS = [SystemId, Color]
    """
    system_id = args[0]
    color = args[1]

    if not validate_system_id(game, system_id):
        return (False, "System id {} is not valid.".format(system_id))

    def count_color(count, value):
        if value == color:
            return count + 1
        else:
            return count

    ships = get_ships_in_system(game, system_id)
    ships_of_color = reduce(count_color, [ship["piece"]["color"] for ship in ships], 0)
    stars_of_color = reduce(count_color, [piece["color"] for piece in game["systems"][system_id]["star"]["pieces"]], 0)
    if ships_of_color + stars_of_color < 4:
        return (False, "That color is not overpopulated in system {}".format(system_id))

    return (True, "")


@schema
def validate_setup(game: GAMESTATE, args: SETUP_ARGS) -> (bool, str):
    """Returns (True, "") if the setup is valid, (False, message) otherwise.
    SETUP_ARGS = (star_pieces: [PIECE], ship: PIECE)
    """
    star_pieces = args[0]
    ship_piece = args[1]
    all_pieces = star_pieces + [ship_piece]
    all_piece_keys = [create_piece_key(piece) for piece in all_pieces]
    for key in set(all_piece_keys):
        if game["reserve"][key] < all_piece_keys.count(key):
            return (False, "Not enough pieces of type {} remaining to do setup.".format(key))

    for _, system in game["systems"].items():
        if system["star"]["owner"] == game["current_player"]:
            return (False, "Current player has already completed setup.")

    return (True, "")


ACTION_VALIDATORS = {
    "construct": validate_construct,
    "move": validate_move,
    "trade": validate_trade,
    "attack": validate_attack,
    "catastrophe": validate_catastrophe,
    "sacrifice": validate_sacrifice,
    "setup": validate_setup
}


##################
# Action methods
# All assume validation has already happened.
##################


@schema
def construct(game: GAMESTATE, system: SystemId, color: Color) -> GAMESTATE:
    """Build a ship of smallest size of color in system."""
    all_size_keys = [color[0] + str(num) for num in range(1, 4)]
    all_size_amounts = [(key, game["reserve"][key]) for key in all_size_keys if game["reserve"][key] > 0]

    if all_size_amounts:
        key, amount = all_size_amounts[0]
        game["reserve"][key] = amount - 1
        game["systems"][system]["ships"].append({"owner":game["current_player"],
                                                 "piece": {"color":color,
                                                           "size": int(key[1])}
                                                })

    return game


@schema
def move(game: GAMESTATE, from_system: ExistingSystemId, ship: SHIP, to_system: SystemId) -> GAMESTATE:
    """Moves a ship from from_system to to_system, destroying from_system if it is a neutral star with
    no other ships.
    Checks for whether homeworlds are destroyed are only done at the end of the turn, outside actions.
    """
    from_ships = game["systems"][from_system]["ships"]
    from_ships = [s for s in from_ships if s != ship]

    if not from_ships and game["systems"][from_system]["star"]["owner"] == NO_OWNER:
        piece = game["systems"][from_system]["star"]["piece"]
        piece_key = piece["color"][0] + str(piece["size"])
        game["reserve"][piece_key] += 1
        del game["systems"][from_system]

    if isinstance(to_system, dict):
        piece = to_system["new_piece"]
        star = {"owner": NO_OWNER, "pieces": [piece]}
        system = {"star": star, "ships": [ship]}
        game["system_count"] += 1
        new_id = game["system_count"]
        game["systems"][new_id] = system
    else:
        game["systems"][to_system]["ships"].append(ship)

    return game


@schema
def trade(game: GAMESTATE, system: SystemId, ship: SHIP, color: Color) -> GAMESTATE:
    """Destroys the given ship and creates a new ship of the same size, but specified color."""
    sys_ships = game["systems"][system]["ships"]
    sys_ships = [s for s in sys_ships if s != ship]

    new_piece = {"size": ship["piece"]["size"], "color": color}
    game = _add_piece_to_reserve(game, ship["piece"])
    game = _remove_piece_from_reserve(game, new_piece)

    new_ship = {"owner": game["current_player"], "piece": new_piece}
    sys_ships.append(new_ship)

    return game


@schema
def attack(game: GAMESTATE, system: SystemId, ship: SHIP) -> GAMESTATE:
    """Changes the owner of ship to be the current player."""
    sys_ship = [s for s in game["systems"][system]["ships"] if s == ship]
    sys_ship["owner"] = game["current_player"]

    return game


@schema
def sacrifice(game: GAMESTATE, system: SystemId, ship: SHIP, subsequent_actions: [(Action, ACTION_ARGS)]) -> GAMESTATE:
    sys = game["systems"][system]
    sys["ships"] = [sh for sh in sys["ships"] if sh != ship]
    game = _add_piece_to_reserve(game, ship["piece"])

    for action, args in subsequent_actions:
        method = ACTION_METHODS[action]
        game = method(game, *args)

    return game


@schema
def catastrophe(game: GAMESTATE, system: SystemId, color: Color) -> GAMESTATE:
    """If system has one star of the specified color, destroys all ships.
    Otherwise, destroys all ships of the specified color."""
    sys = game["systems"][system]
    remaining_stars = [p for p in sys["star"]["pieces"] if p["color"] != color]
    if not remaining_stars:
        for p in sys["star"]["pieces"]:
            game = _add_piece_to_reserve(game, p)
        for s in sys["ships"]:
            game = _add_piece_to_reserve(game, s["piece"])
        del game["systems"][system]
    elif len(remaining_stars) != len(sys["star"]["pieces"]):
        for star in sys["star"]["pieces"]:
            if star not in remaining_stars:
                game = _add_piece_to_reserve(game, star)
        game["systems"][system]["star"]["pieces"] = remaining_stars

        remaining_ships = [sh for sh in get_ships_in_system(game, system) if sh["piece"]["color"] != color]
        lost_ships = [sh for sh in get_ships_in_system(game, system) if sh["piece"]["color"] == color]
        for sh in lost_ships:
            game = _add_piece_to_reserve(game, sh)
        game["systems"][system]["ships"] = remaining_ships
    else:
        remaining_ships = [sh for sh in get_ships_in_system(game, system) if sh["piece"]["color"] != color]
        lost_ships = [sh for sh in get_ships_in_system(game, system) if sh["piece"]["color"] == color]
        for sh in lost_ships:
            game = _add_piece_to_reserve(game, sh["piece"])
        game["systems"][system]["ships"] = remaining_ships

    return game


@schema
def setup(game: GAMESTATE, star_pieces: [PIECE], ship_piece: PIECE) -> GAMESTATE:
    """Takes pieces and alters gamestate to establish a homeworld for current player."""
    star = {"owner": game["current_player"], "pieces": star_pieces}
    for piece in star_pieces:
        game = _remove_piece_from_reserve(game, piece)
    ship = {"owner": game["current_player"], "piece": ship_piece}
    game = _remove_piece_from_reserve(game, ship_piece)
    system = {"star": star, "ships": [ship]}
    game["system_count"] += 1
    game["systems"][game["system_count"]] = system

    return game


ACTION_METHODS = {
    "construct": construct,
    "move": move,
    "attack": attack,
    "trade": trade,
    "catastrophe": catastrophe,
    "sacrifice": sacrifice,
    "setup": setup
}


################
# Action utils
# should not be exposed to clients
################


@schema
def _add_piece_to_reserve(game: GAMESTATE, piece: PIECE) -> GAMESTATE:
    piece_key = create_piece_key(piece)
    game["reserve"][piece_key] += 1
    return game


@schema
def _remove_piece_from_reserve(game: GAMESTATE, piece: PIECE) -> GAMESTATE:
    piece_key = create_piece_key(piece)
    game["reserve"][piece_key] -= 1
    return game
