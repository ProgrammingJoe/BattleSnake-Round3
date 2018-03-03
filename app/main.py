import bottle
import os
import random



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

def compute_distance(snake_head, other_block):
    y_diff = abs(snake_head['y'] - other_block['y'])
    x_diff = abs(snake_head['x'] - other_block['x'])
    return y_diff + x_diff

def compute_food_score(score_x, score_y, x, y):
    block1 = {
        'x': score_x,
        'y': score_y
    }
    block2 = {
        'x': x,
        'y': y
    }
    distance = compute_distance(block1, block2)

    return 6 - distance

def add_food_points(food, board):
    x = food['x']
    y = food['y']
    for horiz in range(-2, 3):
        for vert in range(-2, 3):
            board[x+horiz][y+vert] += compute_food_score(horiz, vert, x, y)

    return board

def plan_attack(scary, neck, head, board):
    if scary:
        board[head['x']+1][head['y']] -= 999
        board[head['x']-1][head['y']] -= 999
        board[head['x']][head['y']+1] -= 999
        board[head['x']][head['y']-1] -= 999
    else:
        if neck['x'] != head['x'] and neck['y'] != head['y']:
            board[head['x']+1][head['y']] += 500
        if neck['x'] != head['x'] and neck['y'] != head['y']:
            board[head['x']-1][head['y']] += 500
        if neck['x'] != head['x'] and neck['y'] != head['y']:
            board[head['x']][head['y']+1] += 500
        if neck['x'] != head['x'] and neck['y'] != head['y']:
            board[head['x']][head['y']-1] += 500

    return board

def plan_survival(body_part, board):
    return board

def dont_kill_yourself(myself, board):
    return board


@bottle.post('/move')
def move():
    data = bottle.request.json

    board = [[0]*data['height'] for _ in range(data['width'])]
    my_head = data['you']['body']['data'][0]

    for food in data['food']['data']:
        if compute_distance(my_head, food) < 5:
            board = add_food_points(food, board)

    for snake in data['snakes']['data']:
        snake_part = 0
        for body_part, index in enum(snake['body']['data']):
            if compute_distance(food, body_part) < 5:
                if(snake_part == 0):
                    if(len(snake['body']['data']) <= len(data['you']['body']['data'])):
                        board = plan_attack(True, snake['body']['data'][index+1], body_part, board)
                    else:
                        board = plan_attack(False, neck, body_part, board)
                else:
                    board = plan_survival(body_part, board)
                snake_part += 1

    for body_part in data['you']['body']['data']:
        board = dont_kill_yourself(body_part, board)

    options = {board[my_head['x']][my_head['y']], board[my_head['x']][my_head['y']], board[my_head['x']][my_head['y']], board[my_head['x']][my_head['y']]}

    direction = min(options)

    directions = ['up', 'down', 'left', 'right']
    direction = random.choice(directions)
    print direction
    return {
        'move': direction,
        'taunt': 'Snakes Everywhere! Ahhh!'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)
