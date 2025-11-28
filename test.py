import requests

ID = 123728

url = f"https://minecraft-heads.com/api/v2/heads/{ID}"

data = requests.get(url)
print(data.text)

name = data["name"]
texture = data["texture"]

command = f"""/give @p minecraft:player_head[
minecraft:custom_name={{"text":"{name}","color":"gold","underlined":true,"bold":true,"italic":false}},
minecraft:lore=[
    {{"text":"Custom Head ID: {ID}","color":"gray","italic":false}},
    {{"text":"www.minecraft-heads.com","color":"blue","italic":false}}
],
profile={{properties:[{{name:"textures",value:"{texture}"}}]}}
] 1"""

print(command)
