import { Client, Routes, SlashCommandBuilder, InteractionType, GatewayIntentBits, ChannelType } from 'discord.js';
import { REST } from '@discordjs/rest';
import { createAudioResource, StreamType, joinVoiceChannel, getVoiceConnection, createAudioPlayer, AudioPlayerStatus, AudioPlayer, entersState } from '@discordjs/voice';
import axios from 'axios';
import fs from 'fs';
import path from 'path'
import sharp from 'sharp'
import { exit } from 'process';

const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36';

const WIKI_URL_BASE = 'https://azurlane.koumakan.jp/wiki/';
const DISCORD_TOKEN = process.env['DISCORD_TOKEN'];
const APPLICATION_ID = process.env['APPLICATION_ID'];

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates] });
const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

let allShips = [];
let allSkins = [];

let curShip = '';
let curSkin = '';

let quotePlayer: AudioPlayer = null;

client.once('ready', () => {
    console.log('Bot ready');

    const firstGuild = client.guilds.cache.map(g => g)[0];
    const existingNickname = firstGuild.members.me.displayName;
    
    if (allShips.includes(existingNickname)) {
        curShip = existingNickname;
        curSkin = 'Default';
        playQuote(0);
    }

    setTimeout(playRandomQuotes, 100);
});

client.on('interactionCreate', async interaction => {
	if (interaction.type !== InteractionType.ApplicationCommandAutocomplete) return;

	if (interaction.commandName === 'transform') {
		const focusedOption = interaction.options.getFocused(true);
        if (focusedOption.name === 'ship') {
            const partialShipName = focusedOption.value.toLowerCase();

            const filteredShips = allShips.filter(s => s.toLowerCase().includes(partialShipName));
            const sortedShips = filteredShips.sort((s1, s2) => s1.toLowerCase().indexOf(partialShipName) - s2.toLowerCase().indexOf(partialShipName)).splice(0, 10);
            const autocompleteOptions = sortedShips.map(s => ({name: s, value: s}));
            await interaction.respond(autocompleteOptions);
        } else if (focusedOption.name === 'skin') {
            const partialSkinName = focusedOption.value.toLowerCase();

            const filteredSkins = allSkins.filter(s => s.toLowerCase().includes(partialSkinName));
            const sortedSkins = filteredSkins.sort((s1, s2) => s1.toLowerCase().indexOf(partialSkinName) - s2.toLowerCase().indexOf(partialSkinName)).splice(0, 10);
            const autocompleteOptions = sortedSkins.map(s => ({name: s, value: s}));
            await interaction.respond(autocompleteOptions);
        }
	}
});

client.on('interactionCreate', async interaction => {
	if (!interaction.isChatInputCommand()) return;
	
    if (interaction.commandName === 'transform') {
        await interaction.deferReply({ ephemeral: false });
        const result = await transformBot(interaction.options.getString('ship'), interaction.options.getString('skin') || 'Default');
        await interaction.editReply(result);
    } else if (interaction.commandName === 'reboot') {
        await interaction.reply({ content: 'Rebooting...', ephemeral: true });
        exit(0);
    }
});

// Indefinitely pick a random quote from the folder and play it
const playRandomQuotes = async () => {
    if (curShip && curSkin) {
        if (!quotePlayer) {
            const quoteNumber = Math.floor(Math.random() * getNumQuotesFor(curShip, curSkin));
            await playQuote(quoteNumber);
        }
    }
    
    const waitTime = Math.ceil(Math.random() * (1000 * 90)) + (1000 * 20);
    setTimeout(playRandomQuotes, waitTime);
};

// Play a quote in all of the servers we're connected to
// For improved reliability we make no assumptions about our VC status
// and therefore attempt to reconnect and rebuild our audio output every time
const playQuote = async (quoteIndex: number): Promise<void> => {
    if (quotePlayer) {
        quotePlayer.stop();
    }
    quotePlayer = createAudioPlayer();

    const quotesFolder = getQuotesFolderFor(curShip, curSkin);
    const quoteFile = path.resolve(`${quotesFolder}/${quoteIndex}.ogg`);
    const resource = createAudioResource(fs.createReadStream(quoteFile), {
        inputType: StreamType.Arbitrary
    });

    joinVoiceChannels();

    const allGuilds = client.guilds.cache.map(g => g);
    for (let i = 0; i < allGuilds.length; i++) {
        const curGuild = allGuilds[i];
        getVoiceConnection(curGuild.id).subscribe(quotePlayer);
        console.log(`Attached to voice channel in guild: ${curGuild.id}`);
    }

    entersState(quotePlayer, AudioPlayerStatus.Playing, 5000).then(() => {
        console.log('Began playing');
        entersState(quotePlayer, AudioPlayerStatus.Idle, 30000).then(() => {
            console.log('Quote ended, stopping');
            quotePlayer.stop();
            quotePlayer = null;
        });  
    });

    setTimeout(() => {
        console.log(`Playing: ${quoteIndex}`);
        console.log(`File: ${quoteFile}`);
        quotePlayer.play(resource);
    }, 1000);
};

// Rejoin the topmost voice channel in all guilds we're a part of
const joinVoiceChannels = () => {
    const allGuilds = client.guilds.cache.map(g => g);

    for (let i = 0; i < allGuilds.length; i++) {
        const curGuild = allGuilds[i];
        let connection = getVoiceConnection(curGuild.id);
        if (!connection) {
            const voiceChannel = curGuild.channels.cache.filter(channel => channel.type === ChannelType.GuildVoice).at(0);
            connection = joinVoiceChannel({
                channelId: voiceChannel.id,
                guildId: curGuild.id,
                adapterCreator: curGuild.voiceAdapterCreator,
                selfMute: false,
                selfDeaf: false
            });
        }
    }
};

// Returns the given text starting after the first occurrence of the target
const skipPast = (text: string, target: string): string => {
    const indexFound = text.indexOf(target);
    if (indexFound === -1) {
        throw new Error('Target string not found!');
    }
    return text.substring(indexFound + target.length);
};

// Extracts the portion of the given text up to the target
const extractUntil = (text: string, target: string): string => {
    const indexFound = text.indexOf(target);
    if (indexFound === -1) {
        throw new Error('Target string not found!');
    }
    return text.substring(0, indexFound);
};

// Gets all the ships 
const getAllShips = async () => {
    const res = await axios.get(`${WIKI_URL_BASE}List_of_Ships`, {
        headers: {
            'User-Agent': USER_AGENT
        }
    });

    let shipListHTML: string = res.data;
    shipListHTML = skipPast(shipListHTML, 'id="Standard_List"');
    shipListHTML = extractUntil(shipListHTML, 'id="Retrofitted_Ships"');

    let allShips = [];

    while (shipListHTML.includes('<td data-sort-value=')) {
        // Parse a ship
        shipListHTML = skipPast(shipListHTML, '<td data-sort-value="');
        shipListHTML = skipPast(shipListHTML, '<a href="/wiki/');
        shipListHTML = skipPast(shipListHTML, 'title="');

        const curShipName = extractUntil(shipListHTML, '"');
        allShips.push(curShipName);

        shipListHTML = skipPast(shipListHTML, '</tr>');
    }
    return allShips;
};

// Get all the skins from the wiki
const getAllSkins = async () => {
    const res = await axios.get(`${WIKI_URL_BASE}Skins`, {
        headers: {
            'User-Agent': USER_AGENT
        }
    });

    let skinListHTML: string = res.data;
    skinListHTML = skipPast(skinListHTML, 'id="List_of_skins"');

    let allSkins = [];

    while (skinListHTML.includes('class="azl-shipcard small"')) {
        skinListHTML = skipPast(skinListHTML, 'class="azl-shipcard small"');
        skinListHTML = skipPast(skinListHTML, 'class="alc-bottom"');
        skinListHTML = skipPast(skinListHTML, '<b>');

        let curSkinName = extractUntil(skinListHTML, '</b>');
        if (curSkinName.endsWith('Skin')) {
            curSkinName = curSkinName.substring(0, curSkinName.length - 4).trim();
        }

        allSkins.push(curSkinName);
    }

    return [...new Set(allSkins), 'Default'];
};

// Transforms the bot into the ship and skin given, plays the intro quote
const transformBot = async (ship: string, skin: string): Promise<string> => {
    if (!allShips.includes(ship)) {
        return `*${ship}* is not a valid ship name.`;
    } else if (!allSkins.includes(skin)) {
        return `*${skin}* is not a valid skin name.`;
    }

    const quotesURL = `${await getURLForShip(ship)}/Quotes`;
    const quoteURLs = await getQuotesFromQuotesPage(quotesURL, skin);

    if (typeof quoteURLs == 'string') {
        // Error state
        return quoteURLs;
    }

    await downloadQuotes(ship, skin, quoteURLs.slice(0, 1));
    await setNameAndPictureTo(ship);

    curShip = ship;
    curSkin = skin;   
    await playQuote(0);
    setTimeout(async () => {
        await downloadQuotes(ship, skin, quoteURLs.slice(1));
    }, 1);

    return `Successfully became ${ship}${skin === 'Default' ? '' : ` [${skin}]`}`;
};

// Use nickname feature to rename ourselves in every server, changes global profile picture to match 
// (no nitro for server specific profile pictures)
const setNameAndPictureTo = async (ship: string): Promise<void> => {
    const allGuilds = client.guilds.cache.map(g => g);
    for (let i = 0; i < allGuilds.length; i++) {
        const curGuild = allGuilds[i];
        await curGuild.members.me.setNickname(ship);
    }

    const resPage = await axios.get(`${WIKI_URL_BASE}${await getURLForShip(ship)}`, {
        headers: {
            'User-Agent': USER_AGENT
        }
    });

    let shipImageURL: string = resPage.data;
    shipImageURL = skipPast(shipImageURL, 'shipgirl-image">');
    shipImageURL = skipPast(shipImageURL, 'src="');
    shipImageURL = extractUntil(shipImageURL, '"');

    console.log(`Changing profile image to: ${shipImageURL}`);
    const resImg = await axios.get(shipImageURL, {
        responseType: 'arraybuffer',
        headers: {
            'User-Agent': USER_AGENT,
        }
    });
    console.log('Got image data');
    let shipImage = sharp(resImg.data);
    const shipImageWidth = (await shipImage.metadata()).width;
    shipImage = shipImage.resize(shipImageWidth, shipImageWidth);
    const shipImageData = await shipImage.toBuffer();
    await client.user.setAvatar(shipImageData);
};

// Get all the quotes from the page URL given for the given skin given
const getQuotesFromQuotesPage = async (pageURL: string, skin:string): Promise<Array<string>|string> => {
    const res = await axios.get(`${WIKI_URL_BASE}${pageURL}`, {
        headers: {
            'User-Agent': USER_AGENT
        }
    });

    let allQuotesHTML: string = res.data;
    allQuotesHTML = skipPast(allQuotesHTML, '<article');
    allQuotesHTML = extractUntil(allQuotesHTML, '</article>');

    // Jump to the header for the given skin
    let skinNameHeader = `">${skin}</span>`;
    if (!allQuotesHTML.includes(skinNameHeader)) {
        skinNameHeader = `">${skin} Skin</span>`
        if (!allQuotesHTML.includes(skinNameHeader)) {
            return `*${skin}* is not a valid skin for the given ship`;
        }
    }
    allQuotesHTML = skipPast(allQuotesHTML, skinNameHeader);
    allQuotesHTML = skipPast(allQuotesHTML, '<tbody>');
    // End our area of interest at the end of the table (only quotes for the correct skin are left)
    let curSkinQuotesHTML = extractUntil(allQuotesHTML, '</tbody>');

    let curSkinQuoteURLs = [];

    while (curSkinQuotesHTML.includes('title="Play"')) {
        curSkinQuotesHTML = skipPast(curSkinQuotesHTML, 'title="Play"');
        curSkinQuotesHTML = skipPast(curSkinQuotesHTML, '<a href="');
        curSkinQuoteURLs.push(extractUntil(curSkinQuotesHTML, '"'));
    }

    if (curSkinQuoteURLs.length == 0) {
        return `${skin} has no voice-lines`;
    } else {
        return curSkinQuoteURLs;
    }
};

// Download all the given quote URLs
const downloadQuotes = async (ship: string, skin: string, quoteURLs: Array<string>): Promise<void> => {
    const folderName = getQuotesFolderFor(ship, skin);
    if (!fs.existsSync(folderName)) {
        fs.mkdirSync(folderName, {recursive: true});
    }

    for (let i = 0; i < quoteURLs.length; i++) {
        console.log(`Downloading ${quoteURLs[i]}`);

        const res = await axios.get(quoteURLs[i], {
            responseType: 'arraybuffer',
            headers: {
                'User-Agent': USER_AGENT
            }
        });

        const fullPath = `${folderName}/${i}.ogg`;
        fs.writeFileSync(fullPath, res.data);
    }
};

// Gets the URL for the wiki page for the given ship
const getURLForShip = async (ship: string): Promise<string> => {
    const res = await axios.get(`${WIKI_URL_BASE}List_of_Ships`, {
        headers: {
            'User-Agent': USER_AGENT
        }
    });

    let shipListHTML: string = res.data;
    shipListHTML = skipPast(shipListHTML, `title="${ship}"`);
    shipListHTML = skipPast(shipListHTML, '<a href="/wiki/');

    const shipURL = extractUntil(shipListHTML, '"');
    return shipURL;
};

// Gets the folder on the local file system we can use to store a ship's quotes
const getQuotesFolderFor = (ship: string, skin: string): string => {
    return `quotes/${Buffer.from(`${ship}${skin}`).toString('base64').replace('/', '_').substring(0, 250)}`;
};

// Gets the number of quotes stored on the local file system for the given ship 
const getNumQuotesFor = (ship: string, skin: string): number => {
    return fs.readdirSync(getQuotesFolderFor(ship, skin)).length;
};

const setupSlashCommands = async () => {
    const transformCommand = new SlashCommandBuilder()
        .setName('transform')
        .setDescription('Transforms into a new ship (with an optional skin)')
        .setDMPermission(false)
        .addStringOption(option =>
            option.setName('ship')
                .setDescription('The name of the ship to transform into')
                .setRequired(true)
                .setAutocomplete(true)
        )
        .addStringOption(option =>
            option.setName('skin')
                .setDescription('The skin of the ship to transform into (uses default skin if none provided)')
                .setRequired(false)
                .setAutocomplete(true)
        )
        .toJSON();

    const rebootCommand = new SlashCommandBuilder()
        .setName('reboot')
        .setDescription('Reboots the bot')
        .setDMPermission(false)
        .toJSON();

    await rest.put(Routes.applicationCommands(APPLICATION_ID), { body: [transformCommand, rebootCommand] });
    console.log('Slash commands updated');
};

getAllShips().then(res => {
    allShips = res;
    console.log(`Loaded all ships: ${allShips.length}`);
    getAllSkins().then(res => {
        allSkins = res;
        console.log(`Loaded all skins: ${allSkins.length}`);
        setupSlashCommands().then(() => {
            client.login(DISCORD_TOKEN);
        });
    });
});