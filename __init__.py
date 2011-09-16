import os
import operator
import boggle
import dawg
import datetime
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
app.config['SECRET_KEY'] = 'SECRET_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
cache = SimpleCache()

dawg.init(
    os.path.join(app.root_path, '_dawg'),
    os.path.join(app.root_path, 'files/twl.dawg'),
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
        return make_rows(str(self.grid))
    @property
    def min_length(self):
        map = {16: 3, 25: 4}
        return map[len(self.grid)]
    def check(self, word):
        if len(word) < self.min_length:
            return False
        if not dawg.is_word(word):
            return False
        if not dawg.find(self.grid, word):
            return False
        return True
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
    now = datetime.datetime.utcnow()
    return Game.query.filter(Game.start <= now).order_by(db.desc('start')).first()

def get_next_game():
    now = datetime.datetime.utcnow()
    return Game.query.filter(Game.start > now).order_by('start').first()

def create_games(day):
    index = 0
    for hour in range(24):
        for minute in range(0, 60, 4):
            start = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            end = start + datetime.timedelta(seconds=180)
            size = 4 + index % 2
            grid = boggle.create(size)
            grid = ''.join(grid)
            game = Game(grid, start, end)
            db.session.add(game)
            index += 1
    db.session.commit()

def purge_games():
    # TODO: improve query
    now = datetime.datetime.utcnow()
    games = Game.query.filter(Game.end < now).all()
    total = 0
    count = 0
    for game in games:
        total += 1
        if not game.entries.count():
            count += 1
            db.session.delete(game)
            db.session.commit()
    db.engine.execute('VACUUM;')
    return count, total

# Hooks
def static(filename):
    return url_for('static', filename=filename)

@app.context_processor
def inject_static():
    return dict(static=static)

@app.before_request
def inject_user():
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

@app.before_request
def inject_game():
    g.now = datetime.datetime.utcnow()
    g.game = get_current_game()
    g.next_game = get_next_game()
    g.words = g.game.get_words()
    g.entries = Entry.query.filter_by(game_id=g.game.id, user_id=g.user.id).order_by('word')
    g.score = sum(entry.score for entry in g.entries)
    scores = db.session.query(Entry.user_id, db.func.sum(Entry.score)).filter_by(game_id=g.game.id).group_by(Entry.user_id).all()
    leaderboard = [(User.query.get(user_id), score) for user_id, score in scores]
    leaderboard.sort(key=operator.itemgetter(1), reverse=True)
    g.leaderboard = leaderboard

# Views
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    game = get_current_game()
    word = request.form['word'].lower()
    if game.state != Game.ACTIVE:
        flash('Game is over.')
    elif game.check(word):
        entry = Entry.query.filter_by(game_id=game.id, user_id=g.user.id, word=word).first()
        if entry:
            flash('You already submitted that word.')
        else:
            entry = Entry(game, g.user, word, boggle.score(word))
            db.session.add(entry)
            db.session.commit()
            flash('+%d points for "%s"' % (entry.score, word))
    else:
        flash('"%s" is not a valid word.' % word)
    return redirect(url_for('index'))

@app.route('/create_games')
def _create_games():
    create_games(datetime.datetime.utcnow())
    return redirect(url_for('index'))

@app.route('/purge_games')
def _purge_games():
    count, total = purge_games()
    flash('Purged %d of %d old games.' % (count, total))
    return redirect(url_for('index'))

# Main
if __name__ == '__main__':
    #reset_db()
    #create_games(datetime.datetime.utcnow())
    app.run(host='0.0.0.0', debug=True, threaded=True)
