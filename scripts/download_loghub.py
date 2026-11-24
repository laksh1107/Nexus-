import argparse, os, urllib.request, zipfile, shutil
URLS={"HDFS":"https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1","BGL":"https://zenodo.org/records/8196385/files/BGL.zip?download=1"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=URLS,required=True)
    args=p.parse_args()
    root=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","data","raw"))
    os.makedirs(root,exist_ok=True)
    dest=os.path.join(root,args.dataset+".zip")
    print("Downloading",args.dataset,"from LogHub / Zenodo. This may take several minutes.")
    urllib.request.urlretrieve(URLS[args.dataset],dest)
    print("Saved",dest)
    with zipfile.ZipFile(dest) as z:z.extractall(os.path.join(root,args.dataset))
    print("Extracted to",os.path.join(root,args.dataset))
if __name__=="__main__":main()
