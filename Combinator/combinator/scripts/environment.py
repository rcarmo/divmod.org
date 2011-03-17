import optparse

from combinator import sysenv

def run():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--projects-dir', metavar='DIR',
        help='locate project working copies in DIR')
    parser.add_option('-p', '--paths-dir', metavar='DIR',
        help='locate Combinator state data in DIR')

    options, args = parser.parse_args()
    sysenv.export(options.projects_dir, options.paths_dir)
