import os
from javascript_fixes import require

os.environ["timeout"] = "1000"
os.environ["TIMEOUT"] = "1000"


class ChromeLauncherAdapter:
    @staticmethod
    def launch(**kwargs):
        chrome_launcher = require("chrome-launcher")
        response = chrome_launcher.launch(kwargs, timeout=300)
        return response
        

if __name__ == "__main__":
    pass