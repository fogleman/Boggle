function _find(grid, word, seen, result, path, index, x, y) {
	var size = grid.length;
	if (x < 0 || y < 0 || x >= size || y >= size) {
		return;
	}
	if (seen[[y, x]]) {
		return;
	}
	var letter = grid[y][x];
	if (letter != word[index]) {
		return;
	}
	seen[[y, x]] = true;
	path.push([y, x]);
	if (index == word.length - 1) {
		result.push(path.slice());
	}
	else {
		for (var dy = -1; dy <= 1; dy++) {
			for (var dx = -1; dx <= 1; dx++) {
				_find(grid, word, seen, result, path, index + 1, x + dx, y + dy);
			}
		}
	}
	path.pop();
	seen[[y, x]] = false;
}

function find(grid, word) {
	var result = [];
	var size = grid.length;
	var seen = [];
	for (var y = 0; y < size; y++) {
		for (var x = 0; x < size; x++) {
			_find(grid, word, seen, result, [], 0, x, y);
		}
	}
	return result;
}

function update() {
	$('td').removeClass('lite');
	var word = $('#word').val();
	var paths = find(grid, word);
	for (var i in paths) {
		var path = paths[i];
		for (var j in path) {
			var pos = path[j];
			$('#' + pos[0] + pos[1]).addClass('lite');
		}
	}
}

$(function() {
	$('#word').focus();
	$('#word').keyup(function() {
		update();
	});
});
