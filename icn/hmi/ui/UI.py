import sys,os
import curses

class UI (object):

	def __init__(self):
		self.height = -1
		self.width = -1
		self.k = 0
		self.cursor_x = 0
		self.cursor_y = 0
		self.elements = []

	def appendElements(self, elements):
		for e in elements: 
			self.elements.append(e) #[UI_Element("Tank 1", 10), UI_Element("Tank 2", 20)]

	def run(self):
		curses.wrapper(self.draw)

	def draw(self, stdscr):
		# Clear and refresh the screen for a blank canvas
		stdscr.clear()
		stdscr.refresh()

		# Start colors in curses
		curses.start_color()
		curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
		curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
		curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

		# Loop where k is the last character pressed
		while (self.k != ord('q')):

			# Initialization
			stdscr.clear()
			self.height, self.width = stdscr.getmaxyx()

			title = ""

			# Declaration of strings
			for e in self.elements: 
				title += e.name + " " + str(e.value) + " | "

			# title = "Tank 1 {} - Tank 2 {}".format(self.getValue(), self.getValue())[:self.width-1]
			subtitle = ""[:self.width-1]
			# keystr = "Last key pressed: {}".format(k)[:self.width-1]
			statusbarstr = "Press 'q' to exit"
			# if k == 0:
			#     keystr = "No key press detected..."[:self.width-1]

			# Centering calculations
			start_x_title = int((self.width // 2) - (len(title) // 2) - len(title) % 2)
			start_x_subtitle = int((self.width // 2) - (len(subtitle) // 2) - len(subtitle) % 2)
			# start_x_keystr = int((self.width // 2) - (len(keystr) // 2) - len(keystr) % 2)
			start_y = int((self.height // 2) - 2)

			# Rendering some text
			# whstr = "Width: {}, Height: {}".format(self.width, self.height)
			# stdscr.addstr(0, 0, whstr, curses.color_pair(1))

			# Render status bar
			stdscr.attron(curses.color_pair(3))
			stdscr.addstr(self.height-1, 0, statusbarstr)
			stdscr.addstr(self.height-1, len(statusbarstr), " " * (self.width - len(statusbarstr) - 1))
			stdscr.attroff(curses.color_pair(3))

			# Turning on attributes for title
			stdscr.attron(curses.color_pair(2))
			stdscr.attron(curses.A_BOLD)

			# Rendering title
			stdscr.addstr(start_y, start_x_title, title)

			# Turning off attributes for title
			stdscr.attroff(curses.color_pair(2))
			stdscr.attroff(curses.A_BOLD)

			# Print rest of text
			stdscr.addstr(start_y + 1, start_x_subtitle, subtitle)
			# stdscr.addstr(start_y + 3, (self.width // 2) - 2, '-' * 4)
			# stdscr.addstr(start_y + 5, start_x_keystr, keystr)
			stdscr.move(self.cursor_y, self.cursor_x)

			# Refresh the screen
			stdscr.refresh()

			# Wait for next input
			self.k = stdscr.getch()