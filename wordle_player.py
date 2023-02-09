import pyperclip as pc
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from wordle_advisor import WordleAdvisor


class WordlePlayer:
    def __init__(self) -> None:
        self.n_letters = 5
        self.n_guesses = 6
        self.guess_count = 0

    def __load_game(self) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")

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

        state = self.__get_tile_state(self.guess_count - 1, self.n_letters - 1, browser)

        return state not in ("empty", "tbd")

    def __is_share_button_loaded(self, browser: WebDriver = None) -> bool:
        if browser is None:
            browser = self.browser

        elements = self.browser.find_elements(by=By.XPATH, value="//*[@data-testid='icon-share']")

        return len(elements) > 0

    def __click_share_button(self) -> None:
        share_button = self.browser.find_element(by=By.XPATH, value="//*[@data-testid='icon-share']")
        share_button.click()

    def add_guess(self, guess: str) -> None:
        self.actions.send_keys(guess + Keys.RETURN)
        self.actions.perform()
        self.guess_count += 1
        self.wait.until(self.__is_last_guess_loaded)

    def get_colors(self) -> str:
        colors = ""
        
        for col in range(self.n_letters):
            state = self.__get_tile_state(self.guess_count - 1, col)
            if state == "absent":
                colors += "b"
            elif state == "present":
                colors += "y"
            elif state == "correct":
                colors += "g"

        return colors

    def play(self, n_jobs: int = -1) -> None:
        self.__init__()
        self.__load_game()
        advisor = WordleAdvisor()

        guess = "raise"
        for i in range(advisor.n_guesses):
            self.add_guess(guess)
            colors = self.get_colors()
            advisor.add_guess(guess, colors)

            if colors == "ggggg":
                break

            guess = advisor.get_best_next_guess(n_jobs)

        self.wait.until(self.__is_share_button_loaded)
        self.__click_share_button()

        print("Guesses:")
        print(advisor.guesses.apply(lambda row: "".join(row), axis=1))
        print("\nColors:")
        print(pc.paste())


if __name__ == "__main__":
    player = WordlePlayer()
    player.play()
