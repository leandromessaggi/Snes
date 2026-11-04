#!/usr/bin/env python3
"""ComfyUI image-to-image adapter. Works only with a user-supplied API workflow.

No API key is stored. Input images remain local unless the operator invokes the
command and explicitly chooses the ComfyUI server to which they are uploaded.
"""
import argparse
import hashlib
import json
import struct
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_PROMPT=(
    "Reimagine this pixel-art sheet as 1997-era pre-rendered PS1 CGI, "
    "low-poly material realism, metallic highlights, detailed sand and "
    "military equipment, consistent isometric camera. Preserve the exact "
    "subject placements, bounding boxes, grid alignment and orientations. "
    "Do not invent or erase elements; no typography."
)

def png_dimensions(data):
    if len(data)<24 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Expected a PNG asset")
    width,height=struct.unpack_from(">II",data,16)
    if not (1<=width<=8192 and 1<=height<=8192):
        raise ValueError("PNG dimensions out of range")
    return width,height

def prepare_workflow(workflow, image_node, text_node, filename, prompt):
    # Workflow must be exported with 'Save (API format)' from ComfyUI.
    nodes=json.loads(json.dumps(workflow))
    if not isinstance(nodes,dict):
        raise ValueError("ComfyUI workflow must be an API-format object")
    try:
        image=nodes[str(image_node)]
        text=nodes[str(text_node)]
        if image["class_type"]!="LoadImage" or text["class_type"]!="CLIPTextEncode":
            raise ValueError("Image/positive prompt nodes must be LoadImage/CLIPTextEncode")
        image["inputs"]["image"]=filename
        text["inputs"]["text"]=prompt
    except KeyError as e:
        raise ValueError("Missing requested workflow node or required input") from e
    return nodes

def request_json(server,route,payload=None,timeout=30):
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(server+route,data=data,headers={
        "Content-Type":"application/json"} if data is not None else {},
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return json.loads(response.read(16*1024*1024))

def upload_png(server,png):
    png_dimensions(png)
    boundary="----romnative"+uuid.uuid4().hex
    filename="rom2native_"+uuid.uuid4().hex+".png"
    start=(
        "--"+boundary+"\r\n"
        'Content-Disposition: form-data; name="image"; filename="'+filename+'"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode("utf-8")
    suffix=("\r\n--"+boundary+"--\r\n").encode("ascii")
    payload=start+png+suffix
    req=urllib.request.Request(server+"/upload/image",data=payload,headers={
        "Content-Type":"multipart/form-data; boundary="+boundary},method="POST")
    with urllib.request.urlopen(req,timeout=60) as response:
        result=json.loads(response.read(1024*1024))
    return result["name"]

def check_server(server,allow_remote):
    parsed=urllib.parse.urlparse(server)
    if parsed.scheme not in ("http","https") or not parsed.netloc:
        raise ValueError("Expected a ComfyUI http(s) URL")
    if not allow_remote and parsed.hostname not in ("localhost","127.0.0.1","::1"):
        raise ValueError("Refusing remote image upload: pass --allow-remote explicitly")
    return server.rstrip("/")

def run(server,workflow,image_node,text_node,source,output,prompt,timeout,allow_remote):
    server=check_server(server,allow_remote)
    source=Path(source);output=Path(output)
    input_bytes=source.read_bytes()
    input_dims=png_dimensions(input_bytes)
    image_name=upload_png(server,input_bytes)
    nodes=prepare_workflow(workflow,image_node,text_node,image_name,prompt)
    job=request_json(server,"/prompt",{"prompt":nodes,"client_id":uuid.uuid4().hex})
    if "prompt_id" not in job:
        raise RuntimeError("ComfyUI did not accept the workflow: "+str(job)[:500])
    prompt_id=job["prompt_id"]
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        response=request_json(server,"/history/"+urllib.parse.quote(prompt_id,safe=""))
        history=response.get(prompt_id,{})
        outputs=history.get("outputs",{})
        for outputNode in outputs.values():
            for image in outputNode.get("images",[]):
                if image.get("type") not in ("output","temp"):continue
                query=urllib.parse.urlencode({
                    "filename":image["filename"],
                    "subfolder":image.get("subfolder",""),
                    "type":image.get("type","output")})
                with urllib.request.urlopen(server+"/view?"+query,timeout=60) as stream:
                    data=stream.read(32*1024*1024+1)
                if len(data)>32*1024*1024:
                    raise ValueError("Generated PNG exceeds limit")
                if png_dimensions(data)!=input_dims:
                    raise ValueError("Generated atlas dimensions differ; fix ComfyUI graph to preserve the tile layout")
                output.parent.mkdir(parents=True,exist_ok=True)
                output.write_bytes(data)
                report={
                    "format":"rom2native-ai-result-v0.1",
                    "model_provider":"ComfyUI user workflow",
                    "source_sha256":hashlib.sha256(input_bytes).hexdigest(),
                    "result_sha256":hashlib.sha256(data).hexdigest(),
                    "source_dimensions":list(input_dims),
                    "style_prompt":prompt,
                    "review_required":True,
                    "warning":"Visual alignment and temporal consistency require manual review."
                }
                output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
                return report
        if history.get("status",{}).get("status_str")=="error":
            raise RuntimeError("ComfyUI reported workflow failure")
        time.sleep(1)
    raise TimeoutError("ComfyUI did not finish before timeout")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--workflow",required=True,type=Path,
        help="API-format ComfyUI graph with LoadImage and CLIPTextEncode nodes")
    parser.add_argument("--image-node",required=True)
    parser.add_argument("--text-node",required=True)
    parser.add_argument("--server",default="http://127.0.0.1:8188")
    parser.add_argument("--prompt",default=DEFAULT_PROMPT)
    parser.add_argument("--timeout",type=int,default=300)
    parser.add_argument("--allow-remote",action="store_true")
    args=parser.parse_args()
    graph=json.loads(args.workflow.read_text(encoding="utf-8"))
    print(json.dumps(run(args.server,graph,args.image_node,args.text_node,
        args.input,args.output,args.prompt,args.timeout,args.allow_remote),indent=2))

if __name__=="__main__":
    main()
