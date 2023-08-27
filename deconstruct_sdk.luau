local fs = require("@lune/fs")
local roblox = require("@lune/roblox")
local process = require("@lune/process")
local luau = require("@lune/luau")
local serde = require("@lune/serde")

local workDir = process.args[1]
local file = fs.readFile(`{workDir}/superbiz.rbxm`)
local superbizSDK = roblox.deserializeModel(file)[1]

local CLASS_NAME_REFER = {
	["Script"] = ".server.lua",
	["LocalScript"] = ".client.lua",
	["ModuleScript"] = ".lua",
}

local function CheckScriptConvert(targetScript, recursive)
	if CLASS_NAME_REFER[targetScript.ClassName] and #targetScript:GetChildren() > 0 then
		local newContainer = roblox.Instance.new("Folder")
		newContainer.Name = targetScript.Name
		newContainer.Parent = targetScript.Parent

		local newScript = targetScript:Clone()
		newScript.Name = "init"
		newScript.Parent = newContainer

		for _, child in pairs(targetScript:GetChildren()) do
			child.Parent = newContainer
			if CLASS_NAME_REFER[child.ClassName] then
				CheckScriptConvert(child, true)
			end
		end

		targetScript:Destroy()
	end
end

local function StartConvertNestedScript()
	for _, item in pairs(superbizSDK:GetChildren()) do
		if CLASS_NAME_REFER[item.ClassName] then
			CheckScriptConvert(item, true)
		end
	end
end

-- Use the FS API to write the file
local function RecursiveGenRojoFolder(targetFolder, targetPath)
	fs.writeDir(targetPath)
	for _, child in pairs(targetFolder:GetChildren()) do
		if child:IsA("Folder") then
			RecursiveGenRojoFolder(child, targetPath .. "/" .. child.Name)
		elseif CLASS_NAME_REFER[child.ClassName] then
			fs.writeFile(targetPath .. "/" .. child.Name .. CLASS_NAME_REFER[child.ClassName], child.Source)
		end
	end
end

local function GetSDKVersion()
	local sdkConfig = superbizSDK:FindFirstChild("InternalConfig")
	if sdkConfig then
		local configFileSrc = sdkConfig.Source
		configFileSrc = "game = { ReplicatedStorage = { FindFirstChild = function() end } }\n" .. configFileSrc -- Monkey patch for SDK
		return luau.load(configFileSrc)().SDK_VERSION or "00"
	end
	return "00"
end

local function CreateRojoProject(SDKName, tree)
	local rojoSDK = {
		-- name = SDKName,
		name = "bloxbiz-sdk",
		tree = tree,
	}
	fs.writeFile(`{workDir}/{SDKName}/default.project.json`, serde.encode("json", rojoSDK))
end

do
	local SDKversion = GetSDKVersion()
	local SDKname = `bloxbiz-sdk-v{SDKversion}`

	StartConvertNestedScript()
	RecursiveGenRojoFolder(superbizSDK, `{workDir}/{SDKname}/src`)
	CreateRojoProject(SDKname, { ["$path"] = "src" })

	print(`{SDKname},{SDKversion}`) -- Send the SDK name back to Python
end
