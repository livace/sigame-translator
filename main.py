import zipfile

import os
import sys
import xml.etree.ElementTree as ET

from googletrans import Translator
import time
import tqdm

import tempfile

def walk(root, result):
    def should_skip(root):
        if not root.text:
            return True

        if root.text.startswith('@'):
            return True

        if root.attrib and 'isRef' in root.attrib and root.attrib['isRef']:
            return True

        if set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя').isdisjoint(root.text.lower()):
            return True

        return False

    if not should_skip(root):
        result.append(root)

    for children in root:
        walk(children, result)


def translate(texts):
    translator = Translator()

    result = []
    bs = 25
    for i in tqdm.tqdm(range(0, len(texts), bs)):
        result += translator.translate('\n'.join(texts[i:i+bs]), dest='en').text.split('\n')
        time.sleep(0.1)

    if len(texts) != len(result):
        for i in range(max(len(texts), len(result))):
            f = texts[i] if i < len(texts) else '[none]'
            t = result[i] if i < len(result) else '[none]'
            print(f'{f} -> {t}')

        assert len(texts) == len(result), f'Expected: {len(result)}, got: {len(texts)}'

    return result


def collect_nodes(root):
    result = []
    walk(root, result)
    return result

def update(dir):
    fname = f'{dir}/content.xml'
    tree_text = open(fname, 'r').read().replace('\n', '  ')
    root = ET.fromstring(tree_text)
    print(tree_text)

    nodes = collect_nodes(root)

    texts = list(map(lambda x: x.text, nodes))

    translated = translate(texts)

    for node, text in zip(nodes, translated):
        print(tree_text)
        # print(f'{node.text} -> {text}')
        tree_text = tree_text.replace(node.text, text)

    open(fname, 'w').write(tree_text)

def unzip_to(file, dir):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(dir)

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
    archive = sys.argv[1]
    dest = f'{archive}.translation.siq'

    with tempfile.TemporaryDirectory() as dir:
        print(f'Unzip to: {dir}')
        unzip_to(archive, dir)
        update(dir)
        zip_back(dest, dir)


if __name__ == '__main__':
    main()
