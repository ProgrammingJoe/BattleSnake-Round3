import bottle
import os
import random
from pandas import *

@bottle.route('/')
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
    data = bottle.request.json
    game_id = data.get('game_id')
    board_width = data.get('width')
    board_height = data.get('height')

    head_url = '%s://%s/static/iguana.jpg' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    return {
        'color': '#6E5D54',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url,
        "head_type": "sand-worm",
        "tail_type": "regular"
    }

def create_layout(data):
    layout = [[0]*data['height'] for _ in range(data['width'])]

    for food in data['food']['data']:
        layout[food['x']][food['y']] = 'food'

    for snake in data['snakes']['data']:
        snake_piece = 0
        snake_length = len(snake['body']['data'])
        for body_part in snake['body']['data']:
            if(snake_piece == 1):
                layout[body_part['x']][body_part['y']] = 'head'
            elif(snake_piece == snake_length - 1):
                layout[body_part['x']][body_part['y']] = 'tail'
            else:
                layout[body_part['x']][body_part['y']] = 'body'

    return layout

def compute_distance(snake_head, other_block):
    y_diff = abs(snake_head['y'] - other_block['y'])
    x_diff = abs(snake_head['x'] - other_block['x'])
    return y_diff + x_diff

def compute_food_score(score_x, score_y, x, y):
    block1 = {
        'x': x,
        'y': y
    }
    block2 = {
        'x': x + score_x,
        'y': y + score_y
    }
    distance = compute_distance(block1, block2)

    return 40 - distance

def compute_bad_score(score_x, score_y, x, y):
    block1 = {
        'x': x,
        'y': y
    }
    block2 = {
        'x': x + score_x,
        'y': y + score_y
    }
    distance = compute_distance(block1, block2)

    if distance == 2:
        return 10
    elif distance == 1:
        return 50
    else:
        return 900

def add_food_points(food, board):
    x = food['x']
    y = food['y']

    for horiz in range(-4, 5):
        for vert in range(-4, 5):
            if 0 <= x+horiz < len(board) and 0 <= y+vert < len(board[0]):
                board[x+horiz][y+vert] += compute_food_score(horiz, vert, x, y)

    return board

def plan_attack(scary, neck, head, board):
    board[head['x']][head['y']] -= 900
    x = head['x']
    y = head['y']

    if scary:
        for horiz in range(-1, 2):
            for vert in range(-1, 2):
                if 0 <= x+horiz < len(board) and 0 <= y+vert < len(board[0]):
                    board[x+horiz][y+vert] -= compute_bad_score(horiz, vert, x, y)
    else:
        if neck['x'] != x and neck['y'] != y:
            if 0 <= x+1 < len(board):
                board[x+1][y] += 500
        if neck['x'] != x and neck['y'] != y:
            if 0 <= x-1 < len(board):
                board[x-1][y] += 500
        if neck['x'] != x and neck['y'] != y:
            if 0 <= y+1 < len(board[0]):
                board[x][y+1] += 500
        if neck['x'] != x and neck['y'] != y:
            if 0 <= y-1 < len(board[0]):
                board[x][y-1] += 500

    return board

def plan_survival(body_part, board):
    board[body_part['x']][body_part['y']] -= 900

    return board

def dont_kill_yourself(myself, board):
    board[myself['x']][myself['y']] -= 900

    return board

def find_chokes(my_head, layout, board):
    x = my_head['x']
    y = my_head['y']

    for horiz in range(-2, 3):
        for vert in range(-2, 3):
            danger_blocks = 0
            if 0 <= x+horiz < len(board) and 0 <= y+vert < len(board[0]):
                # if layout[x+1]
                board[x+horiz][y+vert] += compute_food_score(horiz, vert, x, y)

def get_move(data):
    board = [[0]*data['height'] for _ in range(data['width'])]
    my_head = data['you']['body']['data'][0]
    my_id = data['you']['id']

    layout = create_layout(data)

    # Add food scores
    for food in data['food']['data']:
        if compute_distance(my_head, food) < 40:
            board = add_food_points(food, board)

    # Add snake scores
    for snake in data['snakes']['data']:
        snake_part = 0
        if(not (my_id == snake['id'] or snake['health'] == 0)):
            for index, body_part in enumerate(snake['body']['data']):
                if compute_distance(food, body_part) < 40:
                    if(snake_part == 0):
                        if(len(snake['body']['data']) <= len(data['you']['body']['data'])):
                            board = plan_attack(True, snake['body']['data'][index+1], body_part, board)
                        else:
                            board = plan_attack(False, neck, body_part, board)
                    else:
                        board = plan_survival(body_part, board)
                    snake_part += 1

    # Add my own scores
    for body_part in data['you']['body']['data']:
        board = dont_kill_yourself(body_part, board)

    # Find scary places
    # find_chokes(my_head, layout, board)

    # print DataFrame(board)
    options = dict([])

    if 0 <= my_head['y']-1 < len(board[0]):
        options['left'] = board[my_head['x']][my_head['y']-1]
    if 0 <= my_head['x']+1 < len(board):
        options['down'] = board[my_head['x']+1][my_head['y']]
    if 0 <= my_head['x']-1 < len(board):
        options['up'] = board[my_head['x']-1][my_head['y']]
    if 0 <= my_head['y']+1 < len(board[0]):
        options['right'] = board[my_head['x']][my_head['y']+1]

    direction = min(options, key=options.get)

    # print(options)
    print(direction)

    return {
        'move': direction,
        'taunt': 'Snakes Everywhere! Ahhh!'
    }

@bottle.post('/move')
def move():
    data = bottle.request.json
    get_move(data)

# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    # data = {
    #   "food": {
    #     "data": [
    #       {
    #         "object": "point",
    #         "x": 0,
    #         "y": 0
    #       },
    #       {
    #         "object": "point",
    #         "x": 12,
    #         "y": 12
    #       },
    #       {
    #         "object": "point",
    #         "x": 9,
    #         "y": 13
    #       },
    #       {
    #         "object": "point",
    #         "x": 18,
    #         "y": 3
    #       }
    #     ],
    #     "object": "list"
    #   },
    #   "height": 20,
    #   "id": 1,
    #   "object": "world",
    #   "snakes": {
    #     "data": [
    #       {
    #         "body": {
    #           "data": [
    #             {
    #               "object": "point",
    #               "x": 13,
    #               "y": 19
    #             },
    #             {
    #               "object": "point",
    #               "x": 13,
    #               "y": 18
    #             },
    #             {
    #               "object": "point",
    #               "x": 13,
    #               "y": 17
    #             }
    #           ],
    #           "object": "list"
    #         },
    #         "health": 100,
    #         "id": "58a0142f-4cd7-4d35-9b17-815ec8ff8e70",
    #         "length": 3,
    #         "name": "Sonic Snake",
    #         "object": "snake",
    #         "taunt": "Gotta go fast"
    #       },
    #       {
    #         "body": {
    #           "data": [
    #             {
    #               "object": "point",
    #               "x": 8,
    #               "y": 3
    #             },
    #             {
    #               "object": "point",
    #               "x": 7,
    #               "y": 3
    #             },
    #             {
    #               "object": "point",
    #               "x": 6,
    #               "y": 3
    #             }
    #           ],
    #           "object": "list"
    #         },
    #         "health": 100,
    #         "id": "48ca23a2-dde8-4d0f-b03a-61cc9780427e",
    #         "length": 3,
    #         "name": "Typescript Snake",
    #         "object": "snake",
    #         "taunt": ""
    #       },
    #       {
    #         "body": {
    #           "data": [
    #             {
    #               "object": "point",
    #               "x": 12,
    #               "y": 8
    #             },
    #             {
    #               "object": "point",
    #               "x": 13,
    #               "y": 8
    #             },
    #             {
    #               "object": "point",
    #               "x": 13,
    #               "y": 7
    #             }
    #           ],
    #           "object": "list"
    #         },
    #         "health": 100,
    #         "id": "48ca23a2-dde8-4sefd0f-b03a-61cc9780427e",
    #         "length": 3,
    #         "name": "Typescript Snake",
    #         "object": "snake",
    #         "taunt": ""
    #       }
    #     ],
    #     "object": "list"
    #   },
    #   "turn": 0,
    #   "width": 20,
    #   "you": {
    #     "body": {
    #       "data": [
    #         {
    #           "object": "point",
    #           "x": 19,
    #           "y": 19
    #         },
    #         {
    #           "object": "point",
    #           "x": 8,
    #           "y": 9
    #         },
    #         {
    #           "object": "point",
    #           "x": 8,
    #           "y": 10
    #         }
    #       ],
    #       "object": "list"
    #     },
    #     "health": 100,
    #     "id": "48ca23a2-dde8-4d0f-b03a-61cc9780427e",
    #     "length": 3,
    #     "name": "Typescript Snake",
    #     "object": "snake",
    #     "taunt": ""
    #   }
    # }
    #
    # get_move(data)

    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)
