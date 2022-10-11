#!/usr/bin/env python3

import asyncio
import logging
import os
import time
import traceback

# Libs

import discord # discord.py
import dotenv # python-dotenv

from myylibs.jobsmanager import JobQueue, Job, StatusReport # (provided in myylibs/)
from myylibs.helpers import Helpers # (provided in myylibs/)

from PIL import Image # pillow
# Don't remove, else you might PNG Metadata support
from PIL.PngImagePlugin import PngInfo # pillow

from sdworker import DeguDiffusionWorker # (provided in sdworker.py)

# The code is hideous, with ton of global methods all over
# the place, because I have no idea how to set this up
# using cleanly setup objects while still using Discord.py decorators

# The 'Intents' (Discord privileges and rights) used by bot
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True

# The amount of Debug you want from Discord.py itself
discord.utils.setup_logging(level=logging.INFO)

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = discord.app_commands.CommandTree(self)
        self.sd_queue = None

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)
    
    @staticmethod
    def followup_on(
        response,
        message:str = None,
        file:discord.File = None,
        ephemeral:bool = False):
        
        # For some reason, if you provide an empty content, Discord.py
        # will add '...' to the message, which I really don't like.
        #
        # If you don't set the content at all, though, the problem goes
        # away, so we're on for selecting the arguments we pass... yay...
        kwargs = {}
        if message:
            kwargs["content"] = message
        if file:
            kwargs["file"] = file

        if type(response) == discord.Thread:
            # Discord.py Thread.send doesn't support ephemeral...
            asyncio.ensure_future(response.send(**kwargs))
        else:
            if ephemeral:
                kwargs["ephemeral"] = ephemeral
            asyncio.ensure_future(response.send(**kwargs))

    async def on_member_join(self, member:discord.Member):
        guild = member.guild
        if guild.system_channel is not None:
            to_send = f'Welcome {guild.name} ! You can start using '
            await guild.system_channel.send(to_send)

# Remember, you're limited to 5 fields in a Discord form
# Well, Discord.py will yell at you if you go over 5 fields.
class Generate(discord.ui.Modal, title='Generate'):

    def __init__(self, n_images_data:str="8", prompt_data:str="Degu enjoys its morning coffee by {random_artists}, {random_tags}", inferences_data:str="60", guidance_scale_data:str="7.5", seed_data:str=""):
        
        self.n_images = discord.ui.TextInput(
            label='Number of images',
            style=discord.TextStyle.long,
            placeholder='8',
            default=n_images_data,
            required=True,
            min_length=1,
            max_length=4
        )

        self.prompt = discord.ui.TextInput(
            label='Prompt',
            style=discord.TextStyle.long,
            placeholder='Prompt',
            default=prompt_data,
            required=False,
            max_length=500
        )

        self.seed = discord.ui.TextInput(
            label='Seed',
            required=False,
            default=seed_data,
            style=discord.TextStyle.short
        )

        self.inferences = discord.ui.TextInput(
            label='Inferences',
            default=inferences_data,
            placeholder='60',
            style=discord.TextStyle.short,
            required=True,
            min_length=1,
            max_length=3
        )

        self.guidance_scale = discord.ui.TextInput(
            label='Guidance Scale',
            default=guidance_scale_data,
            placeholder='7.5',
            style=discord.TextStyle.short,
            required=True,
            min_length=1,
            max_length=3
        )

        super().__init__()
        self.add_item(self.n_images)
        self.add_item(self.prompt)
        self.add_item(self.seed)
        self.add_item(self.inferences)
        self.add_item(self.guidance_scale)
        

    def thread_needed(self, n_images:int) -> bool:
        return n_images > MAX_IMAGES_BEFORE_THREAD

    async def on_submit(self, interaction: discord.Interaction):
        prompt = self.prompt.value
        n_images = Helpers.to_int_clamped(self.n_images.value, 8, 1, MAX_IMAGES_PER_JOB)
        n_inferences = Helpers.to_int_clamped(self.inferences.value, 60, 1, MAX_INFERENCES_PER_IMAGE)
        guidance_scale = Helpers.to_float_clamped(self.guidance_scale.value, 7.5, 0, MAX_GUIDANCE_SCALE_PER_IMAGE)

        seed_value = None
        if self.seed.value:
            try:
                seed_value = int(self.seed.value)
            except ValueError:
                pass

        message  = 'Putting your job into the queue\n'
        message += (
            f"Number of images : {n_images}\n"
            f"Prompt : '{prompt}'\n"+
            f"Inferences : {n_inferences}\n"+
            f"Guidance Scale : {guidance_scale}\n")
        if seed_value:
            message += f'Seed : {seed_value}'

        await interaction.response.send_message(message)

        message = await interaction.original_response()
        reference = None
        if self.thread_needed(n_images):
            # Thread titles are limited to 100 characters
            reference = await message.create_thread(name=prompt[:99], reason=f"DeguDiffusion invoked by {interaction.user.name}")
        else:
            reference = interaction.followup

        job = Job(
            external_reference=reference,
            iterations = n_images,
            kwargs = {
                "prompt": prompt,
                "n_inferences": n_inferences,
                "guidance_scale": 7.5,
                "deterministic": seed_value if seed_value else True,
                "width": IMAGES_WIDTH,
                "height": IMAGES_HEIGHT
            }
        )

        interaction.client.sd_queue.add_job(job)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if interaction.response:
            await interaction.followup.send('Oops! Something went wrong.')
        else:
            await interaction.response.send_message('Something went dead wrong...')

        # Make sure we know what the error actually is
        traceback.print_exception(error)

client = MyClient(intents=intents)

@client.tree.command()
async def degudiffusion(interaction: discord.Interaction):
    """Stable Diffusion with more degus !"""
    await interaction.response.send_modal(Generate())

def _png_metadata(png_filepath:str) -> dict:
    ret = {}
    if not os.path.exists(png_filepath):
        print("[_png_metadata] Invalid filepath %s" % (png_filepath))
        return ret
    
    image = Image.open(png_filepath)
    ret = image.text.copy()
    image.close()
    return ret

@client.tree.context_menu(name='Check Degu PNG Metadata')
async def identify_png(interaction: discord.Interaction, message: discord.Message):

    for attachment in message.attachments:
        filename = attachment.filename
        filepath = os.path.join(OUTPUT_DIRECTORY, filename)

        if not os.path.exists(filepath):
            await interaction.response.send_message("I don't remember generating this one...", ephemeral = True)
            return
        else:
            try:
                metadata = _png_metadata(filepath)
                if not metadata:
                    continue
                
                response_content = "Metadata:\n"
                for key in metadata:
                    response_content += ("**%s**: `%s`\n" % (key, metadata[key]))
                
                await interaction.response.send_message(content = response_content, ephemeral=True)
                return
            except Exception as e:
                traceback.print_exception(e)
                await interaction.response.send_message('Something went wrong...', ephemeral = True)
                return

    await interaction.response.send_message("Hmm... could not get anything from this message.", ephemeral = True)
    

@client.tree.context_menu(name='Repeat Diffusion')
async def repeat_diffusion(interaction: discord.Interaction, message: discord.Message):
    """Reinvoke a form with the same Diffusion setup described in this message"""
    if message.author.id != client.user.id:
        await interaction.response.send_message(f"I only analyse {client.user.name} messages at the moment", ephemeral = True)
        return
    
    # That's very fragile, and heavily rely upon Generate() output
    required_fields = {
        "Prompt :": "prompt_data",
        "Inferences :": "inferences_data",
        "Guidance Scale :": "guidance_scale_data",
        "Number of images :": "n_images_data"
    }
    for required_field in required_fields:
        if not ("\n" + required_field) in message.content:
            print("\n\n%s is MISSING\n\n" % (required_field))
            await interaction.response.send_message("Some fields appear missing, so I guess this script isn't updated", ephemeral = True)
            return

    content_lines = message.content.split("\n")


    params = {}
    for line in content_lines:
        for field_name in required_fields:
            if not line.startswith(field_name):
                continue
            param_name = required_fields[field_name]
            treated_line = line.replace(field_name, "").strip()
            params[param_name] = treated_line
            break
        if line.startswith("Seed :"):
            params["seed_data"] = line.replace("Seed :", "").strip()
    
    params["prompt_data"] = params["prompt_data"].strip("'")

    await interaction.response.send_modal(Generate(**params))

@client.event
async def on_ready():
    print(client.guilds)
    print(f'Logged in as {client.user}')
    for guild in client.guilds:
        print(f'Connected to {guild.id}')
        for channel in guild.channels:
            print(f'Channel {channel.name}')

class MyQueue(JobQueue):
    def report_job_started(self, job:Job, report:StatusReport):
        MyClient.followup_on(job.external_reference, message = "Your job has started !", ephemeral = True)

    def report_job_done(self, job:Job, report:StatusReport):
        MyClient.followup_on(job.external_reference, message = "Job finished ! Thanks for using Degu Diffusion !")

    def report_job_progress(self, job:Job, report:StatusReport):
        result = report.result
        if type(result) != dict:
            MyClient.followup_on(job.external_reference, message = "Something went wrong. Yell at a dev !", ephemeral = True)
            return
        
        if not result.keys() >= {"filename", "nsfw", "seed"}:
            MyClient.followup_on(job.external_reference, message = "The image generator is not reporting results correctly. Yell at a dev !", ephemeral = True)
            return

        if result["nsfw"]:
            MyClient.followup_on(job.external_reference, message = "You're too young for this one ! Skipping !", ephemeral = True)
            return

        kwargs = {"response": job.external_reference, "file": discord.File(result["filename"])}

        if not COMPACT_RESPONSES:
            message_content = f"Seed : {result['seed']}\n"
            if result["actual_prompt"]:
                message_content += f"Actual prompt : {result['actual_prompt']}"
            kwargs["message"] = message_content
            
        MyClient.followup_on(**kwargs)
        
    def report_job_failed(self, job:Job, report:StatusReport):
        MyClient.followup_on(job.external_reference, "Ow... The whole thing broke... Try again later, maybe !")
    
    def report_job_canceled(self, job:Job, report:StatusReport):
        MyClient.followup_on(job.external_reference, "Job canceled")

def generate_worker():
    return DeguDiffusionWorker(
        sd_token = os.environ['HUGGINGFACES_TOKEN'],
        output_folder = OUTPUT_DIRECTORY,
        mode = os.environ.get('STABLEDIFFUSION_MODE', 'fp32'))

def get_worker_method(worker:DeguDiffusionWorker):
    return worker.generate_image

async def main_task(client:MyClient):
    queue = MyQueue(generate_worker, get_worker_method)
    client.sd_queue = queue

    await asyncio.gather(
        client.start(os.environ['DISCORD_TOKEN']),
        queue.main_task()
    )

if __name__ == "__main__":
    dotenv.load_dotenv()
    required_environment_variables = [
        "HUGGINGFACES_TOKEN",
        "DISCORD_TOKEN",
        "DISCORD_GUILD_ID"]

    # Check if all vars are present
    missing_vars = []
    for variable_name in required_environment_variables:
        if variable_name not in os.environ:
            missing_vars.append(variable_name)

    if missing_vars:
        print("Some environment variables are missing : %s" % (", ".join(missing_vars)))
        exit(1)

    GUILD = discord.Object(os.environ['DISCORD_GUILD_ID'])
    OUTPUT_DIRECTORY = os.environ.get('IMAGES_OUTPUT_DIRECTORY', 'generated')
    # This tries to get the MAX_IMAGES_PER_JOB environment variable
    # If it exists, it retrieves it and try to parse it. On failure, it fallback to the number 64.
    # If it doesn't exist, it convert the string '64' to the same number.
    MAX_IMAGES_PER_JOB = Helpers.to_int(os.environ.get('MAX_IMAGES_PER_JOB', '64'), 64)
    MAX_INFERENCES_PER_IMAGE = Helpers.to_int(os.environ.get('MAX_INFERENCES_PER_IMAGE', '120'), 120)
    MAX_GUIDANCE_SCALE_PER_IMAGE = Helpers.to_float(os.environ.get('MAX_GUIDANCE_SCALE_PER_IMAGE', '20'), 20)
    IMAGES_WIDTH=Helpers.to_int(os.environ.get('IMAGES_WIDTH', '512'), 512)
    IMAGES_HEIGHT=Helpers.to_int(os.environ.get('IMAGES_HEIGHT', '512'), 512)
    MAX_IMAGES_BEFORE_THREAD=Helpers.to_int(os.environ.get('MAX_IMAGES_BEFORE_THREAD', '2'), 2)
    COMPACT_RESPONSES=False if os.environ.get('COMPACT_RESPONSES', 'False').lower() != "true" else True
    try:
        asyncio.run(main_task(client))
    except:
        if client.sd_queue:
            client.sd_queue._bailing_out()
