# About

This is the code of the first version of my Discord bot named "DeguDiffusion",
which queue generation requests send by Discord users through an in-app form,
execute them with a standard diffusers StableDiffusion setup on the same machine,
and send back the results on the same channel, in a specific thread when seems fit.

![Main view](./screenshots/GenerateForm-Result.png)

The bot has a Job Queue system, allowing you to queue generations
requests and treat them once previous ones finished.

Each batch generates a specific thread, unless its size is lower than
a certain amount, in which cases messages are sent directly on the same channel.

![Messages sent directly](./screenshots/GenerateForm-Result-Direct.png)

This bot won't receive major updates, I'm just uploading this version since it's
working, and want to keep the working version somewhere before I break it
and remake a more versatile one.

![Running bot](./screenshots/RunningBot.png)

# Provided commands

## DeguDiffusion

`/degudiffusion`
Summons a form, where you can setup the generation

![Degu Diffusion](./screenshots/GenerateForm.png)

## Repeat Diffusion

Right-click on a Bot message > Apps > Repeat Diffusion

Summons a form, reusing the settings provided in the message.  
Fails if the message right-clicked contained no diffusion information.

![Apps > Repeat Diffusion](./screenshots/Apps-Repeat-Diffusion.png)
![Generate form](./screenshots/Apps-Repeat-Diffusion-Form.png)

## Check Degu PNG Metadata

Right-click on a generated image message > Apps > Check Degu PNG Metadata

Sends back the metadata of a generated PNG, if it still exist on the server.

![Apps > Check PNG](./screenshots/Apps-CheckPNG.png)
![PNG Metadata](./screenshots/Apps-CheckPNG-Result.png)

> Note : This doesn't try to download the PNG !  
> This ony read it if the server already has it.
>
> Also, this generates ephemeral messages ("Only you can see this message" messages).  
> When sent inside threads, these messages cannot be seen by the client.  
> In this case, just try again.

# Special tags

* `{random_artists}`  
Adds 1 to 5 random artists names
* `{random_tags}`  
Adds 0 to 4 random tags
* `{lyuma_cheatcodes}`  
Try it !

You can add more by editing [replacers.json](replacers.json)

# Running the bot

This is mainly designed to run on a simple Windows PC.  
I haven't tested it on Linux yet.

Execute `STARTBOT.bat` or `STARTBOT.sh`.

## Requirements

You need to be familiar with Python and the installation of
Python libraries.  
There is not autosetup through conda or anything here.

Requirements are :

* Discord.py  
`pip install discord.py`

* HuggingFace StableDiffusion  
See https://huggingface.co/blog/stable_diffusion  
At least : `pip install diffusers==0.4.0 transformers scipy ftfy`

Of course, feel free to adapt this to any *Diffusion you want, by editing
[**sdworker.py**](./sdworker.py).

## Testing SD alone

If you want to test SD itself alone, run `test_stablediffusion_alone.bat` or
`test_stablediffusion_alone.sh`.

This should output 8 images in the output folder (`generated/` by default).  
The prompt used during the tests is :  
**Degu enjoys its morning coffee by {random_artists}, {random_tags}**

If the test fails, check the `HUGGINGFACES_TOKEN` you put in the `.env` file.  
Also pay attention to every line output on the terminal, some of them might
provide clear explanations about what's going on.

See **Configuration** below for how to setup the `.env` file.

## Bots, how do they work ?

A bot is just a special headless Discord client operating with a specific "Bot"
account.

The `DISCORD_TOKEN` is used by the Bot to actually login to Discord.

Bot can run on your machine, and actually this one is actually only tested
in that kind of environment.

### Creating a bot

* Go to the [Discord Developer portal](https://discord.com/developers/applications).
* Create a "New application", by clicking the upper right button near your Profile icon.
* Setup the name.
* In Bot (Left panel), in "Build-A-Bot", click on "Add Bot" and Confirm.
* On Oauth2 General (Left panel), select :
  * **AUTHORIZATION METHOD**  
  In-app Authorization
  * **SCOPES**
    * `bot`
    * `application.commands`
  * **BOT PERMISSIONS**
    * Read Messages / View Channels
    * Send Messages
    * Create Public Threads
    * Send Messages in Threads
    * Attach Files
 * On OAuth2 URL Generator (Left panel) : 
   * Select the same **SCOPES** (`bot` and `application.commands`) and **PERMISSIONS**.
   * Copy the generated URL at the bottom.
* Enter this URL in your browser to add the generated bot to one of your server.  
> You can also send this link to people who'd like to invite the bot to their server.
* In Bot, again, click on 'Reset Token' and save it as `DISCORD_TOKEN` in the `.env` file.

> If the permissions were wrong :  
>   Set the permissions again on both panels  
>   Open the new URL in your browser and invite the Bot again on the same server.

## Configuration

### Requirements

To configure the bot, create a .env file with at least the following variables :

```env
DISCORD_TOKEN=YourDiscordBotToken
DISCORD_GUILD_ID=TheIDOfTheGuildYouWantYourBotIn
HUGGINGFACES_TOKEN=YourHuggingFaceToken
```

You can also copy the commented `.env.sample` to `.env` and edit it.

## How do I get the required informations ?

### Discord Bot Token

If you don't know it, click on "Reset Token" in the "Bot" section of your
application.
You can view your application settings on the [Discord Developer Portal](https://discord.com/developers/applications).

![Reset Discord bot token](./screenshots/Discord-Bot-Token.png)

Once generated, copy the token as `DISCORD_TOKEN` in the `.env` file.

### Discord Guild ID

Note : Guild means Server

When using the Discord application, open the 'User Settings' panel
(Gear icon at the right of your nickname, at the bottom left of the
window), then go to "**App Settings** Advanced" and enable "Developer Mode".

![Enabling Developer mode](./screenshots/HowTo-CopyID-DevMode.png)

Now, right click on the icon of the server you want to get the "Guild ID" from and select "Copy ID".

![Copy the ID](./screenshots/Howto-CopyID.png)

Then copy it as `DISCORD_GUILD_ID` in the `.env` file.

### Huggingface Token

You need to be registered on HuggingFaces.

Then go to "Access Token" from your User Profile and generate or copy your token
in the `.env` file as `HUGGINGFACES_TOKEN`.

![Get an Access Token](./screenshots/Howto-HuggingFaces-Token.png)

Also, note that you also need to accept the licence of StableDiffusion here :  
https://huggingface.co/CompVis/stable-diffusion-v1-4

## Additional configuration

Here's the list of **optional** environment variables you
can define to configure the bot.  
When not defined, their **Default** value will be used.

* `IMAGES_OUTPUT_DIRECTORY`  
  Define where you want to store the generated pictures.  
  **Default** : `generated`  
  Spaces are allowed. No need to use quotes.  
  Example : `IMAGES_OUTPUT_DIRECTORY=another folder`

* `STABLEDIFFUSION_MODE`  
  Allows you to select between different StableDiffusion
  modes. Currently only fp16 and fp32 are supported.  
  **Default** : `fp32`  
  VRAM usage is lower in fp16, so if you're low on VRAM,
  set this to `fp16`.  
  Example : `STABLEDIFFUSION_MODE=fp16`

* `MAX_IMAGES_PER_JOB`  
  Maximum number of images to output per job request.  
  **Default** : `64`  
  That means that the **NUMBER OF IMAGES** typed in `/degudiffusion`
  form will be clamped to that maximum value.  
  Example : `MAX_IMAGES_PER_JOB=8`

* `MAX_INFERENCES_PER_IMAGE`  
  Maximum number of inferences steps per image.  
  **Default** : `120`  
  This clamps the **INFERENCES** number typed in `/degudiffusion`
  form to that maximum value.  
  Example : `MAX_INFERENCES_PER_IMAGE=30`

* `MAX_GUIDANCE_SCALE_PER_IMAGE`  
  Maximal guidance scale allowed.  
  **Default** : `20`  
  This clamps the **GUIDANCE SCALE** number typed in `/degudiffusion`
  form will be clamped to that maximum value.  
  Example : `MAX_GUIDANCE_SCALE_PER_IMAGE=7.5`

* `IMAGES_WIDTH` and `IMAGES_HEIGHT`  
  The width and height of generated images.  
  **Default** : `512`  
  Be ***EXTREMELY*** careful with this one, VRAM usage grows dramatically
  when using higher values.  
  I highly recommend to switch to fp16 when using more than 512x512.  
  Going below 512 in any direction will generally lead to garbage results.  
  Example :  
  `IMAGES_WIDTH=768`  
  `IMAGES_HEIGHT=768`

* `MAX_IMAGES_BEFORE_THREAD`  
  The nuber of images after which the bot will automatically create a thread.  
  **Default** : `2`  
  That means that if you set it to 5 :  
  When requesting up to 5 images per job, the bot will output everything
  on the channel from where the job request was done.  
  When requesting 6 images or more, the bot will create a thread and
  send the results inside this thread.  
  Example : `MAX_IMAGES_BEFORE_THREAD=5`

* `COMPACT_RESPONSES`  
  When set to `True` or `true`, the job response will only include the pictures,
  without any further details (like the Seed, Actual Prompt.).  
  `Default` : False  
  Example : `COMPACT_RESPONSES=True`  
  > You can still use "Check Degu PNG Metadata" when using compact responses.

### Compact mode

Here are two screenshots with :

* Compact mode disabled (default)  
  ![Compact mode disabled](./screenshots/Option-Compact-False.png)

* Compact mode enabled (`COMPACT_RESPONSES=True`)  
  ![Compact mode enabled](./screenshots/Option-Compact-True.png)

# Special notes

If you're not too familiar with StableDiffusion, remember that this
will eat your VRAM for breakfast.

Add `STABLEDIFFUSION_MODE=fp16` to your `.env` if you want to run in
FP16 mode, reducing the amount of VRAM used.  
While this can reduce the amount of VRAM used by 1.5 ~ 2 times,
remember that it's still GPU intensive and VRAM heavy.