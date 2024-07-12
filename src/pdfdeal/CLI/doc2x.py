import argparse
from pdfdeal.Watch.store import (
    get_global_setting,
    change_one_global_setting,
    delete_one_global_setting,
)
import os
from pdfdeal import Doc2X
from pdfdeal.file_tools import get_files
from pdfdeal.Watch.config import curses_select

LANGUAGES = ["简体中文", "Enlish"]
WORDS_CN = [
    "📇 请输入 Doc2X 的身份令牌，个人用户请访问 https://doc2x.noedgeai.com/ 获取, 将会自动保存至本地：",
    "⚠️ 验证 Doc2X 的身份令牌失败，请检查网络连接或者身份令牌是否正确",
    "📌 请选择 Doc2X 的速率限制，单位为次/分钟，强烈建议输入 A 以自动选择速率限制：",
    "🚧 请选择要处理的文件类型:",
    "📂 请输入要处理的文件或文件夹",
    "⚠️ 未找到所在文件或文件夹",
]
WORDS_EN = [
    "📇 Please enter the API key of the Doc2X, for personal use, visit https://doc2x.com/ to get the key, will auto save to local:",
    "⚠️ Failed to verify the API key of Doc2X, please check the network connection or the API key",
    "📌 Please select the rate limit of Doc2X, the unit is times/minute, it is recommended to enter A to automatically select the rate limit:",
    "🚧 Please select the type of file to process:",
    "📂 Please enter the file or folder to deal with:",
    "⚠️ The file or folder does not exist",
]
WORDS = [WORDS_CN, WORDS_EN]


def i18n(language):
    """Maybe the lazy i18n solution, but it works."""
    if language is None:
        language = curses_select(LANGUAGES, "Please select the language:")
    return WORDS[language], language


def set_doc2x_key(language):
    """Set the Doc2X key and rate limit."""
    words, language = i18n(language)
    key = input(words[0])
    try:
        Doc2X(apikey=key)
    except Exception as e:
        raise Exception(f"{words[1]}:\n {e}")
    RPM = input(words[2])
    assert RPM.isdigit() or RPM == "A" or RPM == "a", "The input is invalid."
    if RPM == "A" or RPM == "a":
        if key.startswith("sk-"):
            RPM = 10
        else:
            RPM = 4
    return {"Doc2X_Key": key, "Doc2X_RPM": int(RPM)}, language


def get_file_folder(language):
    words, language = i18n(language)
    while True:
        file_folder = input(words[4])
        if os.path.exists(file_folder):
            break
        print(words[5])
    return file_folder, language


def file_type(language):
    words, language = i18n(language)
    file_type = curses_select(selects=["PDF", "Picture"], show=words[3])
    if file_type == 0:
        return False, True, language
    else:
        return True, False, language


def main():
    parser = argparse.ArgumentParser(
        description="Using doc2x to deal with pictures or pdfs"
    )
    parser.add_argument("filename", help="PDF or picture file/folder", nargs="?")
    parser.add_argument(
        "-y",
        help="Will skip any scenarios that require a second input from the user.",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "-k",
        "--api_key",
        help="The API key of Doc2X, if not set, will use the global setting",
        required=False,
    )
    parser.add_argument(
        "-r",
        "--rpm",
        help="The rate limit of Doc2X, DO NOT set if you don't know",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="The output folder of the result, if not set, will set to './Output'",
        required=False,
    )
    parser.add_argument(
        "-f",
        "--format",
        help="The output format of the result, accept md、md_dollar、latex、docx, default is md_dollar",
        required=False,
        choices=["md", "md_dollar", "latex", "docx"],
    )
    parser.add_argument(
        "-i",
        "--image",
        help="If the input is a picture, set this flag to True, or will ask you",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--pdf",
        help="If the input is a pdf, set this flag to True, or will ask you",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "--equation",
        help="Whether to use the equation model, only works for pictures, default is False",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--clear",
        help="Clear all the global setting about Doc2X",
        required=False,
        action="store_true",
    )
    # Only if need user input, will ask language
    language = None
    args = parser.parse_args()

    if args.clear:
        delete_one_global_setting("Doc2X_Key")
        delete_one_global_setting("Doc2X_RPM")
        print("Clear all the global setting.")

    if args.api_key is None:
        try:
            api_key = str(get_global_setting()["Doc2X_Key"])
            rpm = int(get_global_setting()["Doc2X_RPM"])
            print("Find API: ", api_key[:5] + "*" * (len(api_key) - 10) + api_key[-5:])
        except Exception:
            api_key = None
            print(
                "The global setting does not exist, please set the global setting first."
            )
            doc2x_setting, language = set_doc2x_key(language)
            for key, value in doc2x_setting.items():
                change_one_global_setting(key, value)
            api_key = str(doc2x_setting["Doc2X_Key"])
            rpm = int(doc2x_setting["Doc2X_RPM"])
    else:
        api_key = str(args.api_key)

    rpm = int(args.rpm) if args.rpm else 10 if api_key.startswith("sk-") else 4

    image = args.image
    pdf = args.pdf
    if not image and not pdf:
        image, pdf, language = file_type(language)
    if image and pdf:
        raise ValueError("You can only choose one type of file to process.")

    filename = args.filename

    if filename is None:
        filename, language = get_file_folder(language)

    output = args.output if args.output else "./Output"

    format = args.format if args.format else "md_dollar"

    equation = args.equation

    Client = Doc2X(apikey=api_key, rpm=rpm)

    if image:
        files, rename = get_files(filename, "img", format)
        success, fail, flag = Client.pic2file(
            image_file=files,
            output_path=output,
            output_names=rename,
            output_format=format,
            equation=equation,
        )

    if pdf:
        files, rename = get_files(filename, "pdf", format)
        success, fail, flag = Client.pdf2file(
            pdf_file=files,
            output_path=output,
            output_names=rename,
            output_format=format,
        )


if __name__ == "__main__":
    main()
