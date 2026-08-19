package main

import (
	"fmt"
	"strconv"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

const (
	cellW    = 6
	cellH    = 2
	contentW = cellW - 1
	letterX  = 2

	statusH = 2
)

const (
	tierIdle = iota
	tierWord
	tierCursor
)

type shades struct {
	bg  [3]lipgloss.Color
	fg  lipgloss.Color
	num lipgloss.Color
}

var palette = map[Color]shades{
	EMPTY:     {[3]lipgloss.Color{"#242424", "#31363f", "#414a58"}, "#d8d8d8", "#9aa4b2"},
	SELECTED:  {[3]lipgloss.Color{"#31363f", "#414a58", "#4f5a6b"}, "#ffffff", "#9aa4b2"},
	PARTIAL:   {[3]lipgloss.Color{"#f6e7a8", "#f0db86", "#e8cd5c"}, "#4a3d10", "#66561d"},
	CORRECT:   {[3]lipgloss.Color{"#b6e3c0", "#97d6a6", "#74c78a"}, "#123d20", "#1e4e2d"},
	INCORRECT: {[3]lipgloss.Color{"#f4b8b2", "#ee9c94", "#e57f75"}, "#521a16", "#591f1b"},
}

const (
	blockedBG = lipgloss.Color("#0e0e0e")
	gridBG    = lipgloss.Color("#141414")
	sepFG     = lipgloss.Color("#3d434d")
	accentFG  = lipgloss.Color("#5aa9ff")
	numFG     = lipgloss.Color("#9aa4b2")
	dimFG     = lipgloss.Color("#6b7280")
	labelFG   = lipgloss.Color("#8b95a5")
	titleFG   = lipgloss.Color("#e6e6e6")
)

type model struct {
	g          *Game
	w, h       int
	offX, offY int
	quitting   bool
}

func newModel(g *Game) model { return model{g: g} }

func (m model) Init() tea.Cmd { return nil }

type verifiedMsg struct {
	entry, gen int
	ok         bool
}

func checkCmd(j CheckJob) tea.Cmd {
	return func() tea.Msg {
		return verifiedMsg{
			entry: j.Entry,
			gen:   j.Gen,
			ok:    verifyAnswer([]byte(j.Word), j.Num, j.Across),
		}
	}
}

func (m model) dispatch() tea.Cmd {
	jobs := m.g.PendingChecks()
	if len(jobs) == 0 {
		return nil
	}
	cmds := make([]tea.Cmd, len(jobs))
	for i, j := range jobs {
		cmds[i] = checkCmd(j)
	}
	return tea.Batch(cmds...)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.w, m.h = msg.Width, msg.Height
		m.reclamp()
		return m, nil

	case verifiedMsg:
		m.g.ApplyResult(msg.entry, msg.gen, msg.ok)
		if m.g.Solved() {
			m.quitting = true
			return m, tea.Quit
		}
		return m, nil

	case tea.KeyMsg:
		var cmd tea.Cmd

		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			m.quitting = true
			return m, tea.Quit

		case tea.KeyLeft:
			m.g.Move(DirLeft)
		case tea.KeyRight:
			m.g.Move(DirRight)
		case tea.KeyUp:
			m.g.Move(DirUp)
		case tea.KeyDown:
			m.g.Move(DirDown)

		case tea.KeyBackspace:
			m.g.Backspace()
			cmd = m.dispatch()
		case tea.KeyDelete:
			m.g.Delete()
			cmd = m.dispatch()

		case tea.KeyRunes:
			if len(msg.Runes) == 1 && msg.Runes[0] > ' ' && msg.Runes[0] < 0x7f {
				m.g.Type(msg.Runes[0])
				cmd = m.dispatch()
			}
		}

		m.reclamp()
		return m, cmd
	}

	return m, nil
}

func (m model) viewport() (cols, rows int) {
	cols = min(max((m.w-1)/cellW, 1), Size)
	rows = min(max((m.h-statusH)/cellH, 1), Size)
	return cols, rows
}

func (m *model) reclamp() {
	cols, rows := m.viewport()
	m.offX = min(max(m.offX, m.g.CursorX-cols+1), m.g.CursorX)
	m.offY = min(max(m.offY, m.g.CursorY-rows+1), m.g.CursorY)
	m.offX = min(max(m.offX, 0), Size-cols)
	m.offY = min(max(m.offY, 0), Size-rows)
}

func (m model) View() string {
	if m.quitting || m.w == 0 {
		return ""
	}

	cols, rows := m.viewport()

	var b strings.Builder
	for y := m.offY; y < m.offY+rows; y++ {
		var top, bottom strings.Builder
		for x := m.offX; x < m.offX+cols; x++ {
			m.writeSeparator(&top, &bottom, x, y)
			m.writeCell(&top, &bottom, x, y)
		}
		m.writeSeparator(&top, &bottom, m.offX+cols, y)

		b.WriteString(top.String())
		b.WriteByte('\n')
		b.WriteString(bottom.String())
		b.WriteByte('\n')
	}

	b.WriteString(m.status(cols))
	return b.String()
}

func (m model) writeSeparator(top, bottom *strings.Builder, x, y int) {
	inLeft := x > 0 && x <= Size && m.g.InCurrentWord(x-1, y)
	inRight := x < Size && m.g.InCurrentWord(x, y)

	glyph, fg := "│", sepFG
	if inLeft != inRight {
		glyph, fg = "┃", accentFG
	}

	s := lipgloss.NewStyle().Foreground(fg).Background(gridBG)
	top.WriteString(s.Render(glyph))
	bottom.WriteString(s.Render(glyph))
}

func (m model) writeCell(top, bottom *strings.Builder, x, y int) {
	cell := m.g.Board[y][x]

	if cell.Blocked {
		blank := lipgloss.NewStyle().Background(blockedBG).Render(strings.Repeat(" ", contentW))
		top.WriteString(blank)
		bottom.WriteString(blank)
		return
	}

	tier := tierIdle
	switch {
	case x == m.g.CursorX && y == m.g.CursorY:
		tier = tierCursor
	case m.g.InCurrentWord(x, y):
		tier = tierWord
	}

	upper, lower := palette[cell.Color], palette[cell.Split]
	upperBG, lowerBG := upper.bg[tier], lower.bg[tier]

	num := ""
	if n := m.g.NumberAt(x, y); n != 0 {
		num = strconv.Itoa(n)
	}
	letter := cell.Char
	if letter == "" {
		letter = " "
	}

	if cell.Color == cell.Split {
		numStyle := lipgloss.NewStyle().Foreground(upper.num).Background(upperBG)
		top.WriteString(numStyle.Render(pad(num, contentW)))

		body := lipgloss.NewStyle().Foreground(lower.fg).Background(lowerBG)
		if tier == tierCursor {
			body = body.Bold(true)
		}
		bottom.WriteString(body.Render(padCenter(letter, contentW, letterX)))
		return
	}

	m.writeSplitRow(top, upperBG, lowerBG, 3, pad(num, contentW), upper.num)
	m.writeSplitRow(bottom, upperBG, lowerBG, 1, padCenter(letter, contentW, letterX), lower.fg)
}

func (m model) writeSplitRow(b *strings.Builder, upperBG, lowerBG lipgloss.Color, transition int, text string, textFG lipgloss.Color) {
	runes := []rune(text)
	for i := range contentW {
		switch {
		case i == transition:
			b.WriteString(lipgloss.NewStyle().Foreground(upperBG).Background(lowerBG).Render("▀"))
		case i < transition:
			b.WriteString(lipgloss.NewStyle().Foreground(textFG).Background(upperBG).Render(string(runes[i])))
		default:
			b.WriteString(lipgloss.NewStyle().Foreground(textFG).Background(lowerBG).Render(string(runes[i])))
		}
	}
}

func pad(s string, w int) string {
	if len(s) >= w {
		return s[:w]
	}
	return s + strings.Repeat(" ", w-len(s))
}

func padCenter(s string, w, at int) string {
	return strings.Repeat(" ", at) + s + strings.Repeat(" ", w-at-1)
}

func (m model) status(cols int) string {
	e := m.g.CurrentEntry()
	other := m.g.entries[m.g.EntryAt(m.g.CursorX, m.g.CursorY, turn(m.g.Dir))]

	label := lipgloss.NewStyle().Foreground(labelFG)
	value := lipgloss.NewStyle().Foreground(titleFG).Bold(true)
	dim := lipgloss.NewStyle().Foreground(dimFG)
	accent := lipgloss.NewStyle().Foreground(accentFG).Bold(true)

	line := fmt.Sprintf("%s   %s   %s   %s   %s %s",
		accent.Render(name(e)),
		dim.Render("·"),
		dim.Render("crossing "+name(other)),
		dim.Render("·"),
		label.Render("solved"),
		value.Render(fmt.Sprintf("%d/%d", m.g.SolvedCount(), m.g.TotalCount())),
	)

	if n := m.g.Checking(); n > 0 {
		line += fmt.Sprintf("   %s   %s", dim.Render("·"),
			accent.Render(fmt.Sprintf("checking %d…", n)))
	}

	scroll := ""
	if cols < Size {
		scroll = fmt.Sprintf("   %s   %s", dim.Render("·"),
			dim.Render(fmt.Sprintf("cols %d-%d of %d", m.offX+1, m.offX+cols, Size)))
	}

	return "\n" + line + scroll
}

func name(e Entry) string {
	if e.Across {
		return fmt.Sprintf("%dA", e.Num)
	}
	return fmt.Sprintf("%dD", e.Num)
}

func turn(d Direction) Direction {
	if d.Horizontal() {
		return DirDown
	}
	return DirRight
}
