# encoding=utf-8

"""
This program takes in a read count expression table and a file output prefix. The table is parsed and puts out vector of
transcript ids and its associated count in a pickled gzip compressed file.

"""

import argparse
import os
import pandas as pd
import pickle as pickle
import pyfaidx
import re
import gzip

parser = argparse.ArgumentParser(description='Tissue_expression_profiler')
parser.add_argument('-f',           type=str,        required=True,        metavar='<str>',       help='reference file')
parser.add_argument('-c',           type=str,        required=True,        metavar='<str>',       help='Count table')
parser.add_argument('-o',           type=str,        required=True,        metavar='<str>',       help='output file prefix')


args = parser.parse_args()


file = args.f
count_table = args.c
modelName = args.o


pyfaidx.Faidx(file)

indexFile = ''

for file in os.listdir('.'):
	if file.endswith('.fai'):
		indexFile = os.path.join('.', file)


def parseIndexRef(indexFile):
	"""
	Description:
	Read in sequence data from reference index FASTA file returns a list of transcript IDs
	offset, seqLen, position
	Parameters
	 - indexFile (str): The index file generated by the program, written to the current directory
	Return: The function returns a list of tuples containing the transcript id, start and end offset of the transcript sequence
	"""
	ref_inds = []
	category = []
	fai = open(indexFile, 'r')
	for line in fai:
		splt = line[:-1].split('\t')
		header = '>' + splt[0]
		cat = splt[0].split('|')[-2]
		category.append(cat)
		seqLen = int(splt[1])
		offset = int(splt[2])
		lineLn = int(splt[3])
		nLines = seqLen / lineLn

		if seqLen % lineLn != 0:
			nLines += 1
			ref_inds.append([header, offset, offset + seqLen + nLines])

	fai.close()

	return ref_inds, category


def process_readcounts(count_table):

	# Function to filter count table
	# What % of zero values to include as low expressed
	# Sample randomly from table
	# What is the relationship between the zero-values and the values close to zero?
	# How many of the zero values do we want change with respect to the SD?

	df_count_table = pd.read_csv(count_table, sep=',')
	df1 = df_count_table[df_count_table.IsoPct != 0]
	df1.drop(df1.index)
	read_counts = df1['expected_count'].tolist()

	return read_counts, df1


def create_model(ref):
	
	df_ref = pd.DataFrame(ref, columns=['Transcript_ID', 'start', 'end'])
	df_ref['ENS_transcript_id'] = df_ref['Transcript_ID'].apply(lambda x: re.sub(r"^>(ENST\d*\.\d{1,3})\|.*", r"\1", x))
	table = process_readcounts(count_table)
	df_table = table[1]
	df_result = pd.merge(df_table, df_ref, left_on='transcript_id', right_on='ENS_transcript_id')
	df_result = df_result[['Transcript_ID', 'start', 'end', 'expected_count']]
	total = df_result['expected_count'].sum()
	df_result['proportional_count'] = df_result['expected_count'].div(total)

	return df_result


def main():

	ref_index = parseIndexRef(indexFile)
	ref = ref_index[0]
	categories = ref_index[1]

	model = create_model(ref)
	records = model.to_records(index=False)

	outf = modelName + '_p.gz'
	output = gzip.open(outf, 'wb')
	pickle.dump(records, output)
	pickle.dump(categories, output)


if __name__ == '__main__':
	main()



