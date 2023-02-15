from copy import deepcopy

import pandas as pd
import requests

from utils import parallelize


class WordleAdvisor:
    def __init__(self):
        self.n_letters = 5
        self.n_guesses = 6
        self.guesses = pd.DataFrame(columns=range(self.n_letters))
        self.colors = pd.DataFrame(columns=range(self.n_letters))
        self.solutions = self.__get_complete_word_list()
        self.color_map = self.__get_empty_color_map()

    def __get_complete_word_list(self) -> pd.DataFrame:
        resp = requests.get("https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/c915fa3264be6d35990d0edb8bf927df7a015602/wordle-answers-alphabetical.txt")
        return pd.DataFrame([list(w) for w in resp.text.split("\n")])

    def __get_empty_color_map(self) -> dict:
        return {col: {} for col in ["g", "y", "b"]}

    def __update_color_map(self, guess: str, colors: str, color_map: dict = None) -> None:
        if color_map is None:
            color_map = self.color_map

        for i, (ch, col) in enumerate(zip(guess, colors)):
            col_map = color_map[col]
            if ch not in col_map:
                col_map[ch] = set()
            col_map[ch].add(i)

    def __get_allowed_slots(self, new_color_map: dict, ch: str) -> set:
        allowed_slots = set(range(self.n_letters))

        for color_map in (self.color_map, new_color_map):
            for col in color_map:
                if col == "g":
                    for slots in color_map["g"].values():
                        allowed_slots = allowed_slots.difference(slots)
                elif col in ("y", "b"):
                    allowed_slots = allowed_slots.difference(color_map[col].get(ch, set()))

        return allowed_slots

    def __check_greens(self, new_color_map: dict) -> None:
        for ch, slots in new_color_map["g"].items():
            if len(self.solutions) > 0:
                has_all_greens = (self.solutions[list(slots)] == ch).min(1)
                self.solutions = self.solutions[has_all_greens]

    def __check_yellows(self, new_color_map: dict) -> None:
        self.allowed_slots = {}

        for ch, slots in new_color_map["y"].items():
            if len(self.solutions) > 0:

                min_slots = len(slots)
                max_slots = self.n_letters
                if ch in new_color_map["b"]:
                    max_slots = min_slots

                self.allowed_slots[ch] = self.__get_allowed_slots(new_color_map, ch)
                n_allowed = (self.solutions[list(self.allowed_slots[ch])] == ch).sum(1)
                self.solutions = self.solutions[n_allowed.between(min_slots, max_slots)]

    def __check_blacks(self, new_color_map: dict) -> None:
        for color_map in (self.color_map, new_color_map):
            for ch in color_map["b"]:
                if len(self.solutions) > 0:
                    disallowed_slots = set(range(self.n_letters))
                    for allowed_slots in (new_color_map["g"], self.allowed_slots):
                        disallowed_slots = disallowed_slots.difference(allowed_slots.get(ch, set()))
                    has_no_blacks = (self.solutions[list(disallowed_slots)] != ch).min(1)
                    self.solutions = self.solutions[has_no_blacks]

    def __update_solutions(self, guess: str, colors: str) -> None:
        new_color_map = self.__get_empty_color_map()
        self.__update_color_map(guess, colors, new_color_map)
        self.__check_greens(new_color_map)
        self.__check_yellows(new_color_map)
        self.__check_blacks(new_color_map)

    def __get_colors(self, guess: str, solution: str) -> str:
        colors = ["b"] * 5

        for i in solution[guess == solution].index:
            colors[i] = "g"

        remaining = solution[guess != solution].value_counts().to_dict()
        for i, ch in guess[guess != solution].items():
            if ch in remaining and remaining[ch] > 0:
                colors[i] = "y"
                remaining[ch] -= 1

        return "".join(colors)

    def __get_n_solutions_removed(self, guess: str, solution: str) -> int:
        colors = self.__get_colors(guess, solution)
        w = deepcopy(self)
        w.add_guess(guess, colors)
        return len(self.solutions) - len(w.solutions)

    def __get_avg_solutions_removed(self, guess: str) -> float:
        n = pd.Series(dtype=int)
        for i in self.solutions.index:
            n.loc[i] = self.__get_n_solutions_removed(guess, self.solutions.loc[i])
        return n.mean()

    def get_best_next_guess(self, n_jobs: int = -1) -> str:
        def __get_avg_solutions_removed(guess):
            return self.__get_avg_solutions_removed(guess)

        guess_list = [self.solutions.loc[i] for i in self.solutions.index]
        self.next_guess_scores = pd.Series(
            parallelize(__get_avg_solutions_removed, guess_list, n_jobs=n_jobs),
            index=["".join(self.solutions.loc[i]) for i in self.solutions.index],
        )

        return self.next_guess_scores.idxmax()

    def add_guess(self, guess: str, colors: str) -> None:
        self.guesses.loc[len(self.guesses)] = list(guess)
        self.colors.loc[len(self.colors)] = list(colors)
        self.__update_solutions(guess, colors)
        self.__update_color_map(guess, colors)

    def get_grid_icons(self) -> str:
        icons = ""

        for row in range(len(self.colors)):
            new_icons = "".join(self.colors.iloc[row].map({
                "b": "⬜",
                "y": "🟨",
                "g": "🟩"
            }))
            icons = icons + new_icons + "\n"

        return icons

    def get_guesses(self) -> str:
        guesses = ""

        for row in range(len(self.guesses)):
            new_guess = "".join(self.guesses.iloc[row])
            guesses = guesses + new_guess + "\n"

        return guesses

    def play(self, n_jobs: int = -1) -> None:
        self.__init__()
        for i in range(self.n_guesses):

            if i == 0:
                print(f"Possible solutions: {len(self.solutions)}")
                print("Best first guess: raise")

            guess = input("\nGuess word: ")
            colors = input("Color string (y/g/b): ")

            print("Processing input...")

            self.add_guess(guess, colors)

            if colors == "ggggg":
                print("Congratulations! You have solved the Wordle!")
                break

            else:
                self.get_best_next_guess()
                print(f"Solutions remaining: {len(self.solutions)}")
                print("Top Next Guesses:")
                print(self.next_guess_scores.sort_values(ascending=False).head(5))

        if colors != "ggggg":
            print("Sorry, you did not solve the Wordle.")


if __name__ == "__main__":
    advisor = WordleAdvisor()
    advisor.play()
