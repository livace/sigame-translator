#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import tempfile
import time
import tqdm
import zipfile
import subprocess

import xml.etree.ElementTree as ET

from googletrans import Translator


def parse_args():
    parser = argparse.ArgumentParser('Epic sigame pack translator')
    parser.add_argument('input_file', help='Pack to be translated')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help='Verbose output (spoiler alert)')
    parser.add_argument('--batch-size', '-b', type=int, default=10, help='Batch size')
    return parser.parse_args()


def walk(root, result):
    result.append(root)

    for children in root:
        walk(children, result)


def translate(texts, bs):
    translator = Translator()

    result = []
    for i in tqdm.tqdm(range(0, len(texts), bs)):
        result += translator.translate('\n'.join(texts[i:i+bs]), dest='en').text.split('\n')
        time.sleep(0.1)

    if len(texts) != len(result):
        for i in range(max(len(texts), len(result))):
            f = texts[i] if i < len(texts) else '[none]'
            t = result[i] if i < len(result) else '[none]'
            logging.debug(f'{f} -> {t}')

        assert len(texts) == len(result), f'Expected: {len(result)}, got: {len(texts)}'

    return result


def collect_nodes(root):
    result = []
    walk(root, result)
    return result


def is_text_node(node):
    if not node.text:
        return False

    if node.text.startswith('@'):
        return False

    if node.attrib and 'isRef' in node.attrib and node.attrib['isRef']:
        return False

    return True


def collect_texts(nodes):
    result = []

    def add_if_should_translate(text):
        if not set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя').isdisjoint(text.lower()):
            result.append(text)

    def add_text_if_should(node):
        if is_text_node(node):
            add_if_should_translate(node.text)

    def add_name_if_should(node):
        if not node.attrib:
            return
        if 'name' not in node.attrib:
            return
        add_if_should_translate(node.attrib['name'])

    for node in nodes:
        add_text_if_should(node)
        add_name_if_should(node)

    return list(reversed(sorted(result, key=len)))


def replace_texts(root, trans_dict):
    if is_text_node(root):
        if root.text in trans_dict:
            root.text = trans_dict[root.text]
    for key in root.attrib:
        logging.debug('Attrib: %s -> %s', key, root.attrib[key])
        if root.attrib[key] in trans_dict:
            root.attrib[key] = trans_dict[root.attrib[key]]
    for child in root:
        replace_texts(child, trans_dict)


def update(dir, bs):
    fname = f'{dir}/content.xml'
    tree_text = open(fname, 'r').read().replace('\n', '  ')
    root = ET.fromstring(tree_text)

    logging.debug(tree_text)

    nodes = collect_nodes(root)

    texts = collect_texts(nodes)

    for text in texts:
        logging.debug(f'Will translate {text}')

    translated = translate(texts, bs)

    trans_dict = dict(zip(texts, translated))

    for k, v in trans_dict.items():
        logging.debug('Translation: %s -> %s', k, v)

    replace_texts(root, trans_dict)
    tree_text = ET.tostring(root, encoding='unicode')
    logging.debug(tree_text)
    open(fname, 'w').write(tree_text)


def unzip_to(file, dir):
    logging.info(f'Unzip {file} to: {dir}')
    subprocess.run(
        ['unzip', file, '-d', dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def zip_back(file, dir):
    try:
        os.remove(file)
    except:
        pass

    def zipdir(path, zip_ref):
        for root, dirs, files in os.walk(path):
            for file in files:
                zip_ref.write(os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), path))

    with zipfile.ZipFile(file, 'w') as zip_ref:
        zipdir(dir, zip_ref)


def main():
    args = parse_args()
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        level=logging.INFO if not args.verbose else logging.DEBUG,
    )

    archive = args.input_file
    dest = f'{archive}.translation.siq' if args.output is None else args.output
    logging.info('Destination file: %s', dest)
    logging.info('Batch size: %s', args.batch_size)

    with tempfile.TemporaryDirectory() as dir:
        unzip_to(archive, dir)
        update(dir, args.batch_size)
        zip_back(dest, dir)


if __name__ == '__main__':
    main()
