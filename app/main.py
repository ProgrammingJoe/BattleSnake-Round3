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
        'color': '#5D4E6B',
        'taunt': 'Snakes Everywhere! Ahhh!',
        'head_url': head_url,
        "head_type": "tongue",
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
            if(snake_piece == 0):
                layout[body_part['x']][body_part['y']] = 'head'
            elif(snake_piece == snake_length - 1):
                layout[body_part['x']][body_part['y']] = 'tail'
            else:
                layout[body_part['x']][body_part['y']] = 'body'
            snake_piece += 1

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

    return (10 - distance)

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

    if distance == 1:
        return 100
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
        if neck['x'] != x+1:
            if 0 <= x+1 < len(board):
                board[x+1][y] += 500
        if neck['x'] != x-1:
            if 0 <= x-1 < len(board):
                board[x-1][y] += 500
        if neck['y'] != y+1:
            if 0 <= y+1 < len(board[0]):
                board[x][y+1] += 500
        if neck['y'] != y-1:
            if 0 <= y-1 < len(board[0]):
                board[x][y-1] += 500

    return board

def plan_survival(body_part, board):
    board[body_part['x']][body_part['y']] -= 900

    return board

def dont_kill_yourself(myself, board):
    board[myself['x']][myself['y']] -= 900

    return board

def find_chokes(vertical, my_head, layout, board):
    x = my_head['x']
    y = my_head['y']

    if vertical:
        if(layout[x+1][y-1] in ['head', 'body'] and layout[x-1][y-1] in ['head', 'body']):
            board[x][y-1] -= 300
        elif(layout[x+1][y+1] in ['head', 'body'] and layout[x-1][y+1] in ['head', 'body']):
            board[x][y+1] -= 300
    else:
        if(layout[x+1][y-1] in ['head', 'body'] and layout[x+1][y-1] in ['head', 'body']):
            board[x+1][y] -= 300
        elif(layout[x-1][y+1] in ['head', 'body'] and layout[x-1][y+1] in ['head', 'body']):
            board[x-1][y] -= 300

    return board

def avoid_wall(board):
    width = len(board[0])
    height = len(board)

    for y in range(0, width):
        board[0][y] -= 10
    for y in range(0, width):
        board[height-1][y] -= 10

    for x in range(0, height):
        board[x][0] -= 10
    for x in range(0, height):
        board[x][width-1] -= 10

    return board

def get_move(data):
    board = [[0]*data['height'] for _ in range(data['width'])]
    my_head = data['you']['body']['data'][0]
    my_neck = data['you']['body']['data'][1]
    my_id = data['you']['id']

    # Get my snakes direction
    if(my_head['x'] - my_neck['x'] == 0):
        vertical = True
    else:
        vertical = False

    # Create a layout for debugging
    layout = create_layout(data)

    # Add food scores to the board
    for food in data['food']['data']:
        if compute_distance(my_head, food) < 16:
            board = add_food_points(food, board)

    # Add scores for each snake to the board
    for snake in data['snakes']['data']:
        snake_part = 0
        if(not (my_id == snake['id'] or snake['health'] == 0)):
            for index, body_part in enumerate(snake['body']['data']):
                if compute_distance(food, body_part) < 10:
                    if(snake_part == 0):
                        neck = snake['body']['data'][1]
                        if(len(snake['body']['data']) <= len(data['you']['body']['data'])):
                            board = plan_attack(True, neck, body_part, board)
                        else:
                            board = plan_attack(False, neck, body_part, board)
                        snake_part += 1
                    else:
                        board = plan_survival(body_part, board)
                    snake_part += 1

    # Add my own snake to the board
    for body_part in data['you']['body']['data']:
        board = dont_kill_yourself(body_part, board)

    # Abandoned functionalities
    # board = find_chokes(vertical, my_head, layout, board)
    # board = avoid_wall(board)

    options = dict([])

    # Filter in possible directions
    if 0 <= my_head['y']-1 < len(board):
        options['up'] = board[my_head['x']][my_head['y']-1]
    if 0 <= my_head['x']+1 < len(board[0]):
        options['right'] = board[my_head['x']+1][my_head['y']]
    if 0 <= my_head['x']-1 < len(board[0]):
        options['left'] = board[my_head['x']-1][my_head['y']]
    if 0 <= my_head['y']+1 < len(board):
        options['down'] = board[my_head['x']][my_head['y']+1]

    # Choose the best move
    direction = max(options, key=options.get)

    return {
        'move': direction,
        'taunt': 'Snakes Everywhere! Ahhh!'
    }

@bottle.post('/move')
def move():
    data = bottle.request.json
    return get_move(data)

# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)
