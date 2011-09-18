import boggle
import datetime
import dawg
import operator
import os
import uuid
from flask import Flask, url_for, session, request, g, render_template, flash, redirect
from flaskext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.cache import SimpleCache

'''
Room, Chat, OpenID, Rank
'''

# Constants
ACTIVE_TIMEOUT = 10

# Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = '\x12\x83\xe2\x11\xd8%4aH\x86\xae\x18\xd6R\xe8A\xd0F\x03\xfc\x9b)J\x8f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
cache = SimpleCache()

dawg.init(
    os.path.join(app.root_path, '_dawg'),
    os.path.join(app.root_path, 'files/sowpods.dawg'),
)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64), nullable=False, unique=True)
    remote_addr = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    def __init__(self, uuid, remote_addr, timestamp):
        self.uuid = uuid
        self.remote_addr = remote_addr
        self.timestamp = timestamp
    def __repr__(self):
        return '<User %r>' % self.id

class Game(db.Model):
    PENDING = 1
    ACTIVE = 2
    OVER = 3
    id = db.Column(db.Integer, primary_key=True)
    grid = db.Column(db.String(32), nullable=False)
    start = db.Column(db.DateTime, nullable=False, unique=True)
    end = db.Column(db.DateTime, nullable=False, unique=True)
    def __init__(self, grid, start, end):
        self.grid = grid
        self.start = start
        self.end = end
    @property
    def state(self):
        now = datetime.datetime.utcnow()
        if now < self.start:
            return Game.PENDING
        elif now > self.end:
            return Game.OVER
        else:
            return Game.ACTIVE
    def get_state_display(self):
        map = {
            Game.PENDING: 'Pending',
            Game.ACTIVE: 'Active',
            Game.OVER: 'Over',
        }
        return map[self.state]
    @property
    def rows(self):
        return make_rows(self.grid)
    @property
    def min_length(self):
        map = {16: 3, 25: 4}
        return map[len(self.grid)]
    def check(self, word):
        if len(word) < self.min_length:
            message = 'Words must be at least %d letters long.' % self.min_length
            return False, message
        if not dawg.is_word(word):
            message = '"%s" is not in the dictionary.' % word
            return False, message
        if not dawg.find(self.grid, word):
            message = '"%s" cannot be formed in this puzzle.' % word
            return False, message
        return True, None
    def get_words(self):
        key = 'words_%d' % self.id
        result = cache.get(key)
        if result is None:
            result = boggle.solve(self.rows, self.min_length)
            cache.set(key, result, timeout=300)
        return result
    def __repr__(self):
        return '<Game %r>' % self.id

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    game = db.relationship('Game', backref=db.backref('words', lazy='dynamic', cascade='all, delete'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('entries', lazy='dynamic', cascade='all, delete'))
    word = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('game_id', 'user_id', 'word'),)
    def __init__(self, game, user, word, score):
        self.game = game
        self.user = user
        self.word = word
        self.score = score
    def __repr__(self):
        return '<Entry %r>' % self.id

# Helpers
def reset_db():
    db.drop_all()
    db.create_all()

def make_id():
    return uuid.uuid4().hex

def make_rows(grid):
    map = {16: 4, 25: 5}
    size = map[len(grid)]
    grid = list(reversed(grid))
    rows = []
    for y in xrange(size):
        row = ''.join(grid.pop(-1) for x in xrange(size))
        rows.append(row)
    return rows

def get_active_users():
    timestamp = datetime.datetime.utcnow() - datetime.timedelta(seconds=ACTIVE_TIMEOUT)
    return User.query.filter(User.timestamp >= timestamp)

def get_current_game():
    spacing = datetime.timedelta(seconds=60)
    now = datetime.datetime.utcnow()
    game = Game.query.filter(Game.start <= now).filter(Game.end > now - spacing).order_by(db.desc('start')).first()
    if game is None:
        game = create_game(now, 0)
    return game

def get_next_game():
    now = datetime.datetime.utcnow()
    game = Game.query.filter(Game.start > now).order_by('start').first()
    if game is None:
        game = create_game(now, 1)
    return game

def create_game(when, offset):
    duration = datetime.timedelta(seconds=60 * 3)
    spacing = datetime.timedelta(seconds=60 * 4)
    when = when + spacing * offset
    minute = when.minute - when.minute % 4
    start = when.replace(minute=minute, second=0, microsecond=0)
    end = start + duration
    size = 4 + (minute / 4) % 2
    grid = boggle.create(size)
    grid = ''.join(grid)
    game = Game(grid, start, end)
    db.session.add(game)
    db.session.commit()
    return game

# Hooks
def static(filename):
    return url_for('static', filename=filename)

@app.context_processor
def inject_static():
    return dict(static=static)

@app.before_request
def inject_user():
    if request.endpoint == 'static':
        return
    session.permanent = True
    if 'uuid' in session:
        uuid = session['uuid']
    else:
        uuid = session['uuid'] = make_id()
    user = User.query.filter_by(uuid=uuid).first()
    if user is None:
        user = User(uuid, request.remote_addr, datetime.datetime.utcnow())
        db.session.add(user)
        db.session.commit()
    else:
        user.remote_addr = request.remote_addr
        user.timestamp = datetime.datetime.utcnow()
        db.session.commit()
    g.user = user

# Views
@app.route('/')
def index():
    now = datetime.datetime.utcnow()
    game = get_current_game()
    next_game = get_next_game()
    entries = Entry.query.filter_by(game_id=game.id, user_id=g.user.id).order_by(db.desc('score'), 'word')
    score = sum(entry.score for entry in entries)
    scores = db.session.query(Entry.user_id, db.func.sum(Entry.score)).filter_by(game_id=game.id).group_by(Entry.user_id).all()
    leaderboard = [(User.query.get(user_id), user_score) for user_id, user_score in scores]
    leaderboard.sort(key=operator.itemgetter(1), reverse=True)
    context = {
        'now': now,
        'game': game,
        'next_game': next_game,
        'entries': entries,
        'score': score,
        'leaderboard': leaderboard,
    }
    return render_template('index.html', **context)

@app.route('/submit', methods=['POST'])
def submit():
    game = get_current_game()
    word = request.form['word'].lower()
    valid, message = game.check(word)
    if game.state != Game.ACTIVE:
        flash('The game has ended.')
    elif valid:
        entry = Entry.query.filter_by(game_id=game.id, user_id=g.user.id, word=word).first()
        if entry:
            flash('You already submitted "%s."' % word)
        else:
            entry = Entry(game, g.user, word, boggle.score(word))
            db.session.add(entry)
            db.session.commit()
            flash('+%d points for "%s."' % (entry.score, word))
    else:
        flash(message)
    return redirect(url_for('index'))

# Main
if __name__ == '__main__':
    #reset_db()
    app.run(host='0.0.0.0', debug=True, threaded=True)
