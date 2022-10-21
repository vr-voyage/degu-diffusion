#!/usr/bin/env python3

import json
import random
import os
from typing import NamedTuple
import time
import traceback

from diffusers import StableDiffusionPipeline
from PIL.Image import Image
from PIL.PngImagePlugin import PngInfo
import torch

REPLACERS_FILEPATH="replacers.json"

SpecialTag = NamedTuple('SpecialTag', words=list[str], join_word=str, min=int, max=int, max_occurences=int)

class DeguDiffusionWorker():

    def __init__(self, sd_token:str, output_folder:str, model_name:str="CompVis/stable-diffusion-v1-4", mode:str="fp32", local_only:bool=False, sd_cache_dir:str="", torch_device="cuda"):

        self.model_name = model_name
        self.torch_device = torch_device
        if not output_folder:
            raise ValueError(f"No output directory provided")

        if not os.path.isdir(output_folder):
            raise ValueError(f"The provided images output path doesn't point to a directory :\n{output_folder}")

        pipeline_kwargs = dict()

        if sd_token:
            pipeline_kwargs["use_auth_token"] = sd_token

        if sd_cache_dir:
            if not os.path.isdir(sd_cache_dir):
                raise ValueError(f"The provided StableDiffusion cache path doesn't point to a directory :\n{sd_cache_dir}")
            pipeline_kwargs["cache_dir"] = sd_cache_dir
        
        if local_only:
            pipeline_kwargs["local_files_only"] = True

        if mode == "fp16":
            pipeline_kwargs["revision"] = "fp16"
            pipeline_kwargs["torch_dtype"] = torch.float16

        pipe = StableDiffusionPipeline.from_pretrained(
            self.model_name,
            **pipeline_kwargs)

        pipe = pipe.to(self.torch_device)
        pipe.enable_attention_slicing()
        print(pipe)
        print("StableDiffusion ready to go")

        # Worker specific values
        self.output_folder:str = output_folder
        self.busy = False
        self.pipe = pipe
        self.results = {}
        self.replacers:dict = self.load_replacers(replacers_filepath = REPLACERS_FILEPATH)

    def generate_image(
        self,
        prompt: str = "",
        n_inferences: int = 50,
        guidance_scale: float = 7.5,
        deterministic = True,
        filename_prefix:str = "",
        width = 512,
        height = 512):
        
        report = {}
        generator = None
        seed = 'Unknown'
        if deterministic:
            if type(deterministic) is int:
                seed = deterministic
            else:
                seed = torch.Generator(self.torch_device).seed()
            generator = torch.Generator(self.torch_device).manual_seed(seed)

        original_prompt = prompt
        prompt = self.replace_special_tags(prompt, self.replacers)

        report["actual_prompt"] = prompt if original_prompt != prompt else ""

        metadata = PngInfo()
        metadata.add_itxt("AI_Prompt", str(prompt), lang="utf8", tkey="AI_Prompt")
        metadata.add_text("AI_Torch_Seed", str(seed))
        metadata.add_text("AI_StableDiffusion_Guidance_Scale", str(guidance_scale))
        metadata.add_text("AI_StableDiffusion_Inferences", str(n_inferences))
        metadata.add_text("AI_StableDiffusion_Model_Name", str(self.model_name))
        metadata.add_text("AI_Diffusers_Version", str(self.pipe._diffusers_version))
        metadata.add_text("AI_Metadata_Type", "Voyage")
        metadata.add_text("AI_Metadata_Voyage_Version", "0")
        metadata.add_text("AI_Generator", str(self.model_name))
        metadata.add_text("AI_Torch_Generator", str(self.torch_device))
        metadata.add_text("AI_Custom_Deterministic", str(deterministic))
        
        metadata.add_text("AI_StableDiffusion_Pipe", str(self.pipe))

        with torch.autocast(self.torch_device):
            result = self.pipe(
                prompt,
                width=width,
                height=height,
                guidance_scale=guidance_scale,
                generator=generator,
                num_inference_steps=n_inferences)

        nsfw_flag = result["nsfw_content_detected"][0]
        report["seed"] = seed
        report["nsfw"] = nsfw_flag
        report["filename"] = ""

        if not nsfw_flag:
            image:Image = result.images[0]
            filename = f"{self.output_folder}/{filename_prefix}{int(time.time())}_SEED_{seed}.png"
            image.save(filename, pnginfo=metadata)
            report["filename"] = filename

        return report

    def load_replacers(self, replacers_filepath="replacers.json") -> dict:
        
        replacers:dict = {}

        if not os.path.exists(replacers_filepath):
            print(f"[load_replacers] {replacers_filepath} does not exist")
            return replacers
        
        if not os.path.isfile(replacers_filepath):
            print(f"[load_replacers] {replacers_filepath} is not a file ?? Doing without")
            return replacers

        with open(replacers_filepath, 'r', encoding='utf-8') as f:
            try:
                json_content = json.load(f)
            except Exception as e:
                traceback.print_exception(e)
                print(f"[load_replacers] An error happened when trying to parse the JSON file")
                return replacers

        if not 'replacements' in json_content:
            print(f"[load_replacers] No 'replacements' section in root of the JSON file {replacers_filepath}")
            return replacers

        replacements = json_content['replacements']
        replacements_field_type = type(replacements)
        if not replacements_field_type == dict:
            print(f"[load_replacers] replacements must be an OBJECT (dict).\nCurrently it is a {replacements_field_type}")
            return replacers

        required_fields = {
            "words": list,
            "join_word": str,
            "min": int,
            "max": int,
            "max_occurences": int
        }
        required_field_keys = required_fields.keys()
        for item_name in json_content['replacements']:
            item = replacements[item_name]
            if type(item) != dict:
                print(f"Invalid type for {item}. Skipping")
                continue

            # Yet another obnoxious Python syntax
            item_keys = item.keys()
            if not (item.keys() >= required_field_keys):
                print(f"Missing keys in {item}.\nKeys required : {str(required_field_keys)}\nGot : {str(item_keys)}")
                continue
            
            invalid_fields = []
            for required_field in required_field_keys:
                if type(item[required_field]) != required_fields[required_field]:
                    invalid_fields.append(required_field)
            
            if invalid_fields:
                for invalid_field in invalid_fields:
                    print(f"{invalid_fields} MUST be a {required_fields[invalid_field]}. Currently : {type(item[required_field])}")
                continue
            
            replacer = SpecialTag(
                words=item["words"],
                join_word=item["join_word"],
                min=item["min"],
                max=item["max"],
                max_occurences=item["max_occurences"])
            
            replacers[item_name] = replacer
        
        return replacers
 

    def random_from_tag(self, replacer:SpecialTag) -> list[str]:
        names = replacer.words
        n_names = random.randint(
            min(replacer.min, len(names)),
            min(replacer.max, len(names)))
        return random.sample(names, n_names)

    def replace_special_tags(self, prompt, tags:list[SpecialTag]):

        for tag_name in tags:
            tag:SpecialTag = tags[tag_name]
            if tag == None:
                print("Tag %s has no value ???" % (tag_name))
                continue

            if tag_name not in prompt:
                continue

            occurences = 0
            max_occurences = tag.max_occurences

            while tag_name in prompt:
                if occurences >= max_occurences:
                    prompt = prompt.replace(tag_name, "")
                    break
                
                names_list = self.random_from_tag(tag)

                prompt = prompt.replace(tag_name, tag.join_word.join(names_list), 1)
                occurences += 1
        
        return prompt


if __name__ == "__main__":
    import pathlib

    import dotenv
    from myylibs.helpers import Helpers
    dotenv.load_dotenv()
    # FIXME Factorize this with degu_diffusion into a specific python file.
    # Basically, make a configuration object...
    IMAGES_OUTPUT_DIRECTORY     = os.environ.get('IMAGES_OUTPUT_DIRECTORY', 'generated')
    IMAGES_WIDTH                = Helpers.env_var_to_int('IMAGES_WIDTH', 512)
    IMAGES_HEIGHT               = Helpers.env_var_to_int('IMAGES_HEIGHT', 512)
    STABLEDIFFUSION_LOCAL_ONLY  = False if os.environ.get('STABLEDIFFUSION_LOCAL_ONLY', 'False').lower() != 'true' else True
    HUGGINGFACES_TOKEN          = os.environ.get('HUGGINGFACES_TOKEN', '')
    STABLE_DIFFUSION_MODEL_NAME = os.environ.get('STABLE_DIFFUSION_MODEL_NAME', 'CompVis/stable-diffusion-v1-4')
    TORCH_DEVICE                = os.environ.get('TORCH_DEVICE', 'cuda')
    STABLEDIFFUSION_CACHE_DIR   = os.environ.get('STABLEDIFFUSION_CACHE_DIR', '')

    if STABLEDIFFUSION_CACHE_DIR and (not os.path.exists(STABLEDIFFUSION_CACHE_DIR)):
        pathlib.Path(STABLEDIFFUSION_CACHE_DIR).mkdir(parents = True)

    if (not HUGGINGFACES_TOKEN) and (not STABLEDIFFUSION_LOCAL_ONLY):
        print(
            "At least, either :\n"+
            "* Set the HUGGINGFACES_TOKEN environment variable.\n"+
            "* Set the STABLEDIFFUSION_LOCAL_ONLY environment variable to true\n"+
            "You can also set both, in which case STABLEDIFFUSION_LOCAL_ONLY will take precedence when set to true")
        exit(1)

    if not os.path.exists(IMAGES_OUTPUT_DIRECTORY):
        pathlib.Path(IMAGES_OUTPUT_DIRECTORY).mkdir(parents = True)

    diffuser = DeguDiffusionWorker(
        model_name    = STABLE_DIFFUSION_MODEL_NAME,
        sd_token      = os.environ.get('HUGGINGFACES_TOKEN', ''),
        output_folder = IMAGES_OUTPUT_DIRECTORY,
        mode          = os.environ.get('STABLEDIFFUSION_MODE', 'fp32'),
        sd_cache_dir  = os.environ.get('STABLEDIFFUSION_CACHE_DIR', ''),
        local_only    = STABLEDIFFUSION_LOCAL_ONLY,
        torch_device  = TORCH_DEVICE)
    print("Standalone Stable Diffusion test")

    DEFAULT_IMAGES_PER_JOB    = Helpers.env_var_to_int('DEFAULT_IMAGES_PER_JOB', 8)
    # This is not a formatted string, don't add a f near the quotes
    DEFAULT_PROMPT            = os.environ.get('DEFAULT_PROMPT', 'Degu enjoys its morning coffee by {random_artists}, {random_tags}')
    DEFAULT_SEED              = os.environ.get('DEFAULT_SEED', '')
    DEFAULT_INFERENCES_STEPS  = Helpers.env_var_to_int('DEFAULT_INFERENCES_STEPS', 60)
    DEFAULT_GUIDANCE_SCALE    = Helpers.env_var_to_float('DEFAULT_GUIDANCE_SCALE', 7.5)
    SEED_MINUS_ONE_IS_RANDOM  = True if os.environ.get('SEED_MINUS_ONE_IS_RANDOM', 'True').lower() != "false" else False

    seed_value = None
    if DEFAULT_SEED:
        try:
            seed_value = int(DEFAULT_SEED)
        except ValueError:
            pass
    if seed_value == -1 and SEED_MINUS_ONE_IS_RANDOM:
        seed_value = None

    for _ in range(0, DEFAULT_IMAGES_PER_JOB):
        diffuser.generate_image(
            prompt         = DEFAULT_PROMPT,
            n_inferences   = DEFAULT_INFERENCES_STEPS,
            guidance_scale = DEFAULT_GUIDANCE_SCALE,
            deterministic  = seed_value if seed_value else True,
            width          = IMAGES_WIDTH,
            height         = IMAGES_HEIGHT)
    print(f"Test finished. Check the output in {IMAGES_OUTPUT_DIRECTORY}")
