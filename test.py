import os, requests, time

voiceline_folders = {}

def load_voicelines_for_ship(ship_name: str, skin_name: str):
    print('Loading voicelines for ' + ship_name + ': ' + str(skin_name))

    has_any_voicelines = False
    folder_name = str(time.time())
    os.makedirs('voicelines/' + folder_name)

    ship_name_target_string = '">' + ship_name + '</a>'
    try:
        list_of_ships = requests.get('https://azurlane.koumakan.jp/List_of_Ships', timeout=5).text
    except requests.Timeout:
        return 'The wiki is unavailable or too slow.'

    print('a')

    if ship_name_target_string in list_of_ships:
        list_of_ships = list_of_ships[:list_of_ships.index(ship_name_target_string)]
        new_ship_url = list_of_ships[list_of_ships.rindex('<a href="') + 9:]
        new_ship_url = new_ship_url[:new_ship_url.index('"')]
        new_ship_url = 'https://azurlane.koumakan.jp' + new_ship_url + '/Quotes'

        try:
            list_of_voicelines = requests.get(new_ship_url, timeout=5).text
        except requests.Timeout:
            return 'The wiki is unavailable or too slow.'

        print('b')

        if '<table' in list_of_voicelines:
            if skin_name:
                if skin_name + '</span>' in list_of_voicelines:
                    list_of_voicelines = list_of_voicelines[list_of_voicelines.index(skin_name + '</span>'):]
                else:
                    return 'Skin ' + skin_name + ' not found on the wiki.'

            list_of_voicelines = list_of_voicelines[list_of_voicelines.index('<table') : list_of_voicelines.index('</table')]

            voiceline_target_string = '.ogg" title="Play" class="sm2_button">Play</a>'

            file_index = 0
            while voiceline_target_string in list_of_voicelines:
                cur_voiceline_url = list_of_voicelines[:list_of_voicelines.index(voiceline_target_string) + 4]
                cur_voiceline_url = cur_voiceline_url[cur_voiceline_url.rindex('<a href="') + 9:]


                print('-')
                try:
                    cur_voiceline_bytes = requests.get(cur_voiceline_url, timeout=5).content
                except (requests.Timeout, requests.ConnectionError):
                    return 'The wiki is unavailable or too slow.'

                

                with open('voicelines/' + folder_name + '/voiceline-' + str(file_index) + '.ogg', 'wb') as cur_voiceline_file:
                    cur_voiceline_file.write(cur_voiceline_bytes)

                print(file_index)

                list_of_voicelines = list_of_voicelines[list_of_voicelines.index(voiceline_target_string) + 1:]
                file_index += 1
                has_any_voicelines = True
        else:
            return 'Nice try.'
    else:
        return 'Name not found on the wiki.'
    
    if has_any_voicelines:
        voiceline_folders[ship_name] = folder_name
        return None
    else:
        return 'No voicelines found on the wiki.'

print(load_voicelines_for_ship('Li\'l Sandy', None))