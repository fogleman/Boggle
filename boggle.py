import random
import dawg

DICE4 = [
    'aaeegn',
    'elrtty',
    'aoottw',
    'abbjoo',
    'ehrtvw',
    'cimotu',
    'distty',
    'eiosst',
    'delrvy',
    'achops',
    'himnqu',
    'eeinsu',
    'eeghnw',
    'affkps',
    'hlnnrz',
    'deilrx',
]

DICE5 = [
    'aaafrs',
    'aaeeee',
    'aafirs',
    'adennn',
    'aeeeem',
    'aeegmu',
    'aegmnn',
    'afirsy',
    'bjkqxz',
    'ccnstw',
    'ceiilt',
    'ceilpt',
    'ceipst',
    'ddlnor',
    'dhhlor',
    'dhhnot',
    'dhlnor',
    'eiiitt',
    'emottt',
    'ensssu',
    'fiprsy',
    'gorrvw',
    'hiprry',
    'nootuw',
    'ooottu',
]

def create(size):
    map = {
        4: DICE4,
        5: DICE5,
    }
    dice = list(map[size])
    random.shuffle(dice)
    rows = []
    for y in xrange(size):
        row = ''.join(random.choice(dice.pop(-1)) for x in xrange(size))
        rows.append(row)
    return rows

def _solve(grid, seen, result, letters, x, y):
    size = len(grid)
    if x < 0 or x >= size or y < 0 or y >= size:
        return
    if (x, y) in seen:
        return
    letter = grid[y][x]
    if not dawg.check(letters, letter):
        return
    if letter == 'q':
        if not dawg.check(letters + ['q'], 'u'):
            return
        letter = 'qu'
    seen.add((x, y))
    letters.append(letter)
    if dawg.check(letters, '$'):
        word = ''.join(letters)
        result.add(word)
    for dy in xrange(-1, 2):
        for dx in xrange(-1, 2):
            _solve(grid, seen, result, letters, x + dx, y + dy)
    letters.pop(-1)
    seen.remove((x, y))

def solve(grid, min_length=0):
    result = set()
    size = len(grid)
    for y in xrange(size):
        for x in xrange(size):
            _solve(grid, set(), result, [], x, y)
    result = [x for x in result if len(x) >= min_length]
    result.sort()
    result.sort(key=len, reverse=True)
    return result

def _find(grid, word, seen, result, path, index, x, y):
    size = len(grid)
    if x < 0 or x >= size or y < 0 or y >= size:
        return
    if (x, y) in seen:
        return
    letter = grid[y][x]
    if letter != word[index]:
        return
    seen.add((x, y))
    path.append((x, y))
    if index == len(word) - 1:
        result.append(list(path))
    else:
        for dy in xrange(-1, 2):
            for dx in xrange(-1, 2):
                _find(grid, word, seen, result, path, index + 1, x + dx, y + dy)
    path.pop(-1)
    seen.remove((x, y))

def find(grid, word):
    result = []
    size = len(grid)
    for y in xrange(size):
        for x in xrange(size):
            _find(grid, word, set(), result, [], 0, x, y)
    return result

def score(word):
    map = {
        3: 1,
        4: 1,
        5: 2,
        6: 3,
        7: 5,
    }
    length = len(word)
    if length < 3:
        return 0
    return map.get(length, 11)

def main():
    grid = create(4)
    print '\n'.join(grid)
    words = solve(grid, 3)
    print len(words)
    print sum(score(x) for x in words)
    print words

if __name__ == '__main__':
    main()
