package main

import "strings"

const Size = 21

type Color int

const (
	EMPTY Color = iota
	SELECTED
	PARTIAL
	CORRECT
	INCORRECT
)

type Cell struct {
	Char    string
	Color   Color
	Split   Color
	Blocked bool
}

type Direction int

const (
	DirRight Direction = iota
	DirLeft
	DirDown
	DirUp
)

func (d Direction) Horizontal() bool { return d == DirRight || d == DirLeft }

func (d Direction) Delta() (int, int) {
	switch d {
	case DirRight:
		return 1, 0
	case DirLeft:
		return -1, 0
	case DirDown:
		return 0, 1
	default:
		return 0, -1
	}
}

func (d Direction) Reverse() Direction {
	switch d {
	case DirRight:
		return DirLeft
	case DirLeft:
		return DirRight
	case DirDown:
		return DirUp
	default:
		return DirDown
	}
}

type Entry struct {
	Num    int
	X, Y   int
	Len    int
	Across bool
}

type wordState int

const (
	wordIncomplete wordState = iota
	wordCorrect
	wordIncorrect
)

type Game struct {
	Board   [Size][Size]Cell
	CursorX int
	CursorY int
	Dir     Direction

	entries []Entry
	states  []wordState
	dirty   []bool

	gen     []int
	pending int

	acrossAt [Size][Size]int
	downAt   [Size][Size]int
}

func NewGame() *Game {
	g := &Game{Dir: DirRight}

	for y := range Size {
		for x := range Size {
			g.Board[y][x].Blocked = layout[y][x] == '#'
			g.acrossAt[y][x] = -1
			g.downAt[y][x] = -1
		}
	}

	num := 0
	for y := range Size {
		for x := range Size {
			if g.Board[y][x].Blocked {
				continue
			}
			startsAcross := x == 0 || g.Board[y][x-1].Blocked
			startsDown := y == 0 || g.Board[y-1][x].Blocked
			if !startsAcross && !startsDown {
				continue
			}
			num++
			if startsAcross {
				g.addEntry(num, x, y, true)
			}
			if startsDown {
				g.addEntry(num, x, y, false)
			}
		}
	}

	g.states = make([]wordState, len(g.entries))
	g.dirty = make([]bool, len(g.entries))
	g.gen = make([]int, len(g.entries))
	g.CursorX, g.CursorY = g.entries[0].X, g.entries[0].Y
	g.recolor()
	return g
}

func (g *Game) addEntry(num, x, y int, across bool) {
	idx := len(g.entries)
	e := Entry{Num: num, X: x, Y: y, Across: across}

	cx, cy := x, y
	for cx < Size && cy < Size && !g.Board[cy][cx].Blocked {
		if across {
			g.acrossAt[cy][cx] = idx
			cx++
		} else {
			g.downAt[cy][cx] = idx
			cy++
		}
		e.Len++
	}

	g.entries = append(g.entries, e)
}

func (g *Game) EntryAt(x, y int, d Direction) int {
	if d.Horizontal() {
		return g.acrossAt[y][x]
	}
	return g.downAt[y][x]
}

func (g *Game) NumberAt(x, y int) int {
	if i := g.acrossAt[y][x]; i >= 0 {
		if e := g.entries[i]; e.X == x && e.Y == y {
			return e.Num
		}
	}
	if i := g.downAt[y][x]; i >= 0 {
		if e := g.entries[i]; e.X == x && e.Y == y {
			return e.Num
		}
	}
	return 0
}

func (g *Game) CurrentEntry() Entry {
	return g.entries[g.EntryAt(g.CursorX, g.CursorY, g.Dir)]
}

func (g *Game) InCurrentWord(x, y int) bool {
	if g.Board[y][x].Blocked {
		return false
	}
	return g.EntryAt(x, y, g.Dir) == g.EntryAt(g.CursorX, g.CursorY, g.Dir)
}

func (g *Game) open(x, y int) bool {
	return x >= 0 && x < Size && y >= 0 && y < Size && !g.Board[y][x].Blocked
}

func (g *Game) step(x, y int, d Direction) (int, int, bool) {
	dx, dy := d.Delta()
	for {
		x, y = x+dx, y+dy
		if x < 0 || x >= Size || y < 0 || y >= Size {
			return 0, 0, false
		}
		if !g.Board[y][x].Blocked {
			return x, y, true
		}
	}
}

func (g *Game) Move(d Direction) {
	if d.Horizontal() != g.Dir.Horizontal() {
		g.Dir = d
		return
	}
	g.Dir = d
	if x, y, ok := g.step(g.CursorX, g.CursorY, d); ok {
		g.CursorX, g.CursorY = x, y
	}
}

func (g *Game) Type(ch rune) {
	g.set(g.CursorX, g.CursorY, string(ch))

	dx, dy := g.Dir.Delta()
	if nx, ny := g.CursorX+dx, g.CursorY+dy; g.open(nx, ny) {
		g.CursorX, g.CursorY = nx, ny
	}
}

func (g *Game) Backspace() {
	if g.Board[g.CursorY][g.CursorX].Char == "" {
		dx, dy := g.Dir.Reverse().Delta()
		if px, py := g.CursorX+dx, g.CursorY+dy; g.open(px, py) {
			g.CursorX, g.CursorY = px, py
		}
	}
	g.set(g.CursorX, g.CursorY, "")
}

func (g *Game) Delete() { g.set(g.CursorX, g.CursorY, "") }

func (g *Game) set(x, y int, ch string) {
	if g.Board[y][x].Blocked || g.Board[y][x].Char == ch {
		return
	}
	g.Board[y][x].Char = ch
	g.invalidate(g.acrossAt[y][x])
	g.invalidate(g.downAt[y][x])

	g.recolor()
}

func (g *Game) invalidate(i int) {
	g.gen[i]++
	g.states[i] = wordIncomplete
	g.dirty[i] = true
}

func (g *Game) word(i int) (string, bool) {
	e := g.entries[i]
	var b strings.Builder
	x, y := e.X, e.Y
	for range e.Len {
		ch := g.Board[y][x].Char
		if ch == "" {
			return "", false
		}
		b.WriteString(ch)
		if e.Across {
			x++
		} else {
			y++
		}
	}
	return b.String(), true
}

type CheckJob struct {
	Entry  int
	Gen    int
	Num    int
	Across bool
	Word   string
}

func (g *Game) PendingChecks() []CheckJob {
	var jobs []CheckJob
	for i := range g.entries {
		if !g.dirty[i] {
			continue
		}
		g.dirty[i] = false

		w, full := g.word(i)
		if !full {
			continue
		}
		g.pending++
		jobs = append(jobs, CheckJob{
			Entry:  i,
			Gen:    g.gen[i],
			Num:    g.entries[i].Num,
			Across: g.entries[i].Across,
			Word:   w,
		})
	}
	g.recolor()
	return jobs
}

func (g *Game) ApplyResult(entry, gen int, ok bool) {
	g.pending--
	if gen != g.gen[entry] {
		return
	}
	if ok {
		g.states[entry] = wordCorrect
	} else {
		g.states[entry] = wordIncorrect
	}
	g.recolor()
}

func (g *Game) Checking() int { return g.pending }

func (g *Game) Solved() bool {
	for _, s := range g.states {
		if s != wordCorrect {
			return false
		}
	}
	return true
}

func (g *Game) SolvedCount() int {
	n := 0
	for _, s := range g.states {
		if s == wordCorrect {
			n++
		}
	}
	return n
}

func (g *Game) TotalCount() int { return len(g.entries) }

func (g *Game) recolor() {
	for y := range Size {
		for x := range Size {
			c := &g.Board[y][x]
			if c.Blocked {
				continue
			}
			if c.Char == "" {
				c.Color, c.Split = EMPTY, EMPTY
				continue
			}
			c.Color, c.Split = combine(g.states[g.acrossAt[y][x]], g.states[g.downAt[y][x]])
		}
	}
}

func combine(across, down wordState) (Color, Color) {
	switch {
	case across == wordCorrect && down == wordIncorrect:
		return CORRECT, INCORRECT
	case across == wordIncorrect && down == wordCorrect:
		return INCORRECT, CORRECT
	case across == wordCorrect || down == wordCorrect:
		return CORRECT, CORRECT
	case across == wordIncorrect || down == wordIncorrect:
		return INCORRECT, INCORRECT
	default:
		return PARTIAL, PARTIAL
	}
}
