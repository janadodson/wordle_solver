from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from wordle_advisor import WordleAdvisor


class WordlePlayer:
    def __init__(self, headless: bool = True) -> None:
        self.advisor = WordleAdvisor()
        self.guess_count = 0
        self.headless = headless

    def __load_game(self) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument("--no-sandbox")
        if self.headless:
            options.add_argument("--headless")

        self.browser = webdriver.Chrome(options=options)
        self.actions = ActionChains(self.browser)
        self.wait = WebDriverWait(self.browser, 30, 1)

        self.browser.get("https://www.nytimes.com/games/wordle/index.html")
        self.actions.send_keys(Keys.ESCAPE)
        self.actions.perform()

    def __get_tile_state(self, row: int, col: int, browser: WebDriver = None) -> str:
        if browser is None:
            browser = self.browser

        tile_element = browser.find_elements(by=By.XPATH, value=f"//div[@aria-label='Row {row + 1}']//div[@aria-roledescription='tile']")[col]

        return tile_element.get_attribute("data-state")

    def __is_last_guess_loaded(self, browser: WebDriver = None) -> bool:
        if browser is None:
            browser = self.browser

        if self.guess_count == 0:
            return False

        state = self.__get_tile_state(self.guess_count - 1, self.advisor.n_letters - 1, browser)

        return state not in ("empty", "tbd")

    def add_guess(self, guess: str) -> None:
        self.actions.send_keys(guess + Keys.RETURN)
        self.actions.perform()
        self.guess_count += 1
        self.wait.until(self.__is_last_guess_loaded)

    def get_colors(self) -> str:
        colors = ""

        for col in range(self.advisor.n_letters):
            state = self.__get_tile_state(self.guess_count - 1, col)
            if state == "absent":
                colors += "b"
            elif state == "present":
                colors += "y"
            elif state == "correct":
                colors += "g"

        return colors

    def play(self, n_jobs: int = -1) -> None:
        self.__init__(headless=self.headless)
        self.__load_game()

        guess = "raise"
        for i in range(self.advisor.n_guesses):
            print(f"Guess {i}: {guess}")
            
            self.add_guess(guess)
            colors = self.get_colors()
            self.advisor.add_guess(guess, colors)

            if colors == "ggggg":
                break

            guess = self.advisor.get_best_next_guess(n_jobs)


if __name__ == "__main__":
    player = WordlePlayer(headless=False)
    player.play()

    print("\nColors:")
    print(player.advisor.get_grid_icons())
