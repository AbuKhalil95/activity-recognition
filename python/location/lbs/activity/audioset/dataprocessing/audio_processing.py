# This Python file is an extended/modified version of Jerry Wu's audio_prep.py
# This python file is a script to download a given label from AudioSet
# The downloaded audios would be clipped into 10 seconds periods
# The downloaded audio segments are then processed using Librosa to extract features
# Stored in eval_segments, balanced_train, and unblalanced_train separately.

# Usage: python3 audio_prep.py <label>


from __future__ import unicode_literals
import youtube_dl
import csv
import json
from pydub import AudioSegment
import os
import shutil
from os import listdir
from os.path import isfile, join
import sys
import numpy as np
import librosa
import argparse

referDoc = "ReferDoc/"
downloaded_audio = []
feature_dict = {}

def setup_commandline_args():
  parser = argparse.ArgumentParser(description = 'Process dataset.csv to input into TensorFlow.')
  parser.add_argument('-d', '--datasets', required = True, type = str, nargs = '+')
  parser.add_argument('-r', '--redo', action = 'store_true', required = False)
  parser.add_argument('-l', '--labels', required = True, type = str, nargs = '+')
  args = parser.parse_args()
  print(args)
  return args

def parse_csv(csv_file):
  # Extract all labeled audio info from csv
  # input: str csv_file
  # output: list audio_list
  audio_list = []
  with open(csv_file, newline='') as csvfile:
    info = csv.reader(csvfile, delimiter=' ', quotechar='|')
    for row in info:
      r = ','.join(row)
      if '#' not in r:
        r_lst = r.split(',')
        url, start_time, end_time = r_lst[0], float(r_lst[2]), float(r_lst[4])
        audio_list.append([url, start_time, end_time])
  return audio_list

def label_id_search(label):
	# Reads in the label, and finds the corresponding id in ontology.json
	# input: str label
	# output: str label_encode
	with open(referDoc+"ontology.json") as f:
		labelInfo = json.load(f)
	for info in labelInfo:
		if info["name"] == label:
			return info["id"]
	return None

def download(dest_dir, video_id, redo):
  # Download labeled audio from given url to a dest folder
  # input: str destDir, str video_id
  # output: boolean
  try:
    os.mkdir(dest_dir)
  except OSError as error:
	  print(error)

  # check to see if the video_id has already been downloaded and skip the download if it is already
  # downloaded unless the -r, --redo flag has been passed
  if not redo and isfile(dest_dir + 'sliced_' + video_id):
      print('Already processed video')
      return False

  ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors':[{
      'key': 'FFmpegExtractAudio',
      'preferredquality': '192',
    }],
    # Force the file naming of outputs.
    'outtmpl': dest_dir + '/tmp/' + video_id + '.%(ext)s'
  }
  with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    try:
      ydl.download(['https://www.youtube.com/watch?v='+ video_id])
      downloaded_audio.append(video_id)
      return True
    except:
      print('Downloading Failed.')
      return False

def chop_audio(dest_dir, video_id, start_time, end_time):
	# Chop the whole audio, 
	# and save only the target part labelled by start_time and end_time.
	# Then remove the original audio.
	# input: str video_id, str dest_dir, float start_time, float end_time
	# output: None
	onlyfile = [f for f in listdir(dest_dir+'/tmp') if isfile(join(dest_dir +'/tmp', f))][0]
	if onlyfile.endswith('.m4a'):
		total = AudioSegment.from_file(dest_dir+'/tmp/'+ video_id +'.m4a', 'm4a')
	elif onlyfile.endswith('.opus'):
		total = AudioSegment.from_file(dest_dir+'/tmp/'+ video_id +'.opus', codec='opus')
	else:
		shutil.rmtree(dest_dir +'/tmp/')
		return None
	sliced = total[start_time * 1000: end_time * 1000]
	sliced.export(dest_dir + '/sliced_'+ video_id +'.wav', format='wav')
	shutil.rmtree(dest_dir + '/tmp/')

def extract_features(src_dir):
  # Extract features from all downloaded audio segments from given AudioSet csv list to a dest folder
  # input: str src_dir
  # output: None

  # Extract the following features from each downloaded 10 second audio segment using librosa
  # Extracts the following features: chroma_stft, chroma_cqt, chroma_cens, melspectogram,
  #                                  mfcc, rms, spectral_centroid, spectral_bandwidth,
  #                                  spectral_contrast, spectral_flatness, spectral_rolloff,
  #                                  poly_features, tonnetz, zero_crossing_rate
  for video_id in downloaded_audio:
    f_dict = {}
    prefix = "sliced_"
    suffix = ".wav"
    # extract chroma_stft
    y, sr = librosa.load(src_dir + "/" + prefix + video_id + suffix)
    f_dict["chroma_stft"] = librosa.feature.chroma_stft(y, sr)
    # extract chroma_cqt
    f_dict["chroma_cqt"] = librosa.feature.chroma_cqt(y, sr)
    # extract chroma_cens
    f_dict["chroma_cens"] = librosa.feature.chroma_cens(y, sr)
    # extract melspectrogram
    f_dict["melspectrogram"] = librosa.feature.melspectrogram(y, sr)
    # extract mfcc
    f_dict["mfcc"] = librosa.feature.mfcc(y, sr)
    # extract rms
    f_dict["rms"] = librosa.feature.rms(y)
    # extract spectral_centroid
    f_dict["spectral_centroid"] = librosa.feature.spectral_centroid(y, sr)
    # extract spectral_bandwidth
    f_dict["spectral_bandwidth"] = librosa.feature.spectral_bandwidth(y, sr)
    # extract spectral_contrast
    f_dict["spectral_contrast"] = librosa.feature.spectral_contrast(y, sr)
    # extract spectral_flatness
    f_dict["spectral_flatness"] = librosa.feature.spectral_flatness(y)
    # extract spectral_rolloff
    f_dict["spectral_rolloff"] = librosa.feature.spectral_rolloff(y, sr)
    # extract poly_features
    f_dict["poly_features"] = librosa.feature.poly_features(y, sr)
    # extract tonnetz
    f_dict["tonnetz"] = librosa.feature.tonnetz(y, sr)
    # extract zero_crossing_rate
    f_dict["zero_crossing_rate"] = librosa.feature.zero_crossing_rate(y, sr)
    feature_dict[video_id] = f_dict

def main(csv_file, redo):
  audio_list = parse_csv(referDoc + csv_file)
  for video_id, start_time, end_time in audio_list:
    success = download('audio_balanced_train', video_id, redo)
    if success:
      chop_audio('audio_balanced_train', video_id, start_time, end_time)
      extract_features('audio_balanced_train')

if __name__ == "__main__":
  args = setup_commandline_args()
  main(args.datasets[0], args.redo)
