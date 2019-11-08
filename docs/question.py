# -*- coding: utf-8 -*-
"""
    question
    ~~~~~~~~~~~~~~~
Based on sphinx.ext.todo, cut down.
https://github.com/jpcw/sphinxcontrib-gen_node is really what we want, but it doesn't work
on current versions of sphinx.
    Allow todos to be inserted into your documentation.  Inclusion of todos can
    be switched of by a configuration variable.  The todolist directive collects
    all todos of your project and lists them along with a backlink to the
    original location.
    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.admonitions import BaseAdmonition

import sphinx
from sphinx.environment import NoUri
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import set_source_info
from sphinx.util.texescape import tex_escape_map

logger = logging.getLogger(__name__)


class question_node(nodes.Admonition, nodes.Element):
    pass


class questionlist(nodes.General, nodes.Element):
    pass


class Question(BaseAdmonition, SphinxDirective):
    node_class = question_node
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'class': directives.class_option,
    }

    def run(self):
        # type: () -> List[nodes.Node]
        if not self.options.get('class'):
            self.options['class'] = ['admonition-question admonition-todo']

        (todo,) = super(Question, self).run()
        if isinstance(todo, nodes.system_message):
            return [todo]

        todo.insert(0, nodes.title(text=_('Question')))
        set_source_info(self, todo)

        targetid = 'index-%s' % self.env.new_serialno('index')
        # Stash the target to be retrieved later in latex_visit_todo_node.
        todo['targetref'] = '%s:%s' % (self.env.docname, targetid)
        targetnode = nodes.target('', '', ids=[targetid])
        return [targetnode, todo]

def process_questions(app, doctree):
    # type: (Sphinx, nodes.Node) -> None
    # collect all todos in the environment
    # this is not done in the directive itself because it some transformations
    # must have already been run, e.g. substitutions
    env = app.builder.env
    if not hasattr(env, 'question_all_questions'):
        env.question_all_questions = []  # type: ignore
    for node in doctree.traverse(question_node):
        app.emit('question-defined', node)

        try:
            targetnode = node.parent[node.parent.index(node) - 1]
            if not isinstance(targetnode, nodes.target):
                raise IndexError
        except IndexError:
            targetnode = None
        newnode = node.deepcopy()
        del newnode['ids']
        env.question_all_questions.append({  # type: ignore
            'docname': env.docname,
            'source': node.source or env.doc2path(env.docname),
            'lineno': node.line,
            'todo': newnode,
            'target': targetnode,
        })

        if env.config.todo_emit_warnings:
            logger.warning(__("TODO entry found: %s"), node[1].astext(),
                           location=node)


class QuestionList(SphinxDirective):
    """
    A list of all question entries.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[todolist]
        # Simply insert an empty todolist node which will be replaced later
        # when process_todo_nodes is called
        return [questionlist('')]


def process_question_nodes(app, doctree, fromdocname):
    # type: (Sphinx, nodes.Node, unicode) -> None

    # Replace all todolist nodes with a list of the collected todos.
    # Augment each todo with a backlink to the original location.
    env = app.builder.env

    if not hasattr(env, 'question_all_questions'):
        env.question_all_questions = []  # type: ignore

    for node in doctree.traverse(questionlist):
        if node.get('ids'):
            content = [nodes.target()]
        else:
            content = []

        if not app.config['question_include_questions']:
            node.replace_self(content)
            continue

        for todo_info in env.question_all_questions:  # type: ignore
            para = nodes.paragraph(classes=['question-source'])
            if app.config['question_link_only']:
                description = _('<<original entry>>')
            else:
                description = (
                    _('(The <<original entry>> is located in %s, line %d.)') %
                    (todo_info['source'], todo_info['lineno'])
                )
            desc1 = description[:description.find('<<')]
            desc2 = description[description.find('>>') + 2:]
            para += nodes.Text(desc1, desc1)

            # Create a reference
            newnode = nodes.reference('', '', internal=True)
            innernode = nodes.emphasis(_('original entry'), _('original entry'))
            try:
                newnode['refuri'] = app.builder.get_relative_uri(
                    fromdocname, todo_info['docname'])
                newnode['refuri'] += '#' + todo_info['target']['refid']
            except NoUri:
                # ignore if no URI can be determined, e.g. for LaTeX output
                pass
            newnode.append(innernode)
            para += newnode
            para += nodes.Text(desc2, desc2)

            todo_entry = todo_info['todo']
            # Remove targetref from the (copied) node to avoid emitting a
            # duplicate label of the original entry when we walk this node.
            if 'targetref' in todo_entry:
                del todo_entry['targetref']

            # (Recursively) resolve references in the todo content
            env.resolve_references(todo_entry, todo_info['docname'],
                                   app.builder)

            # Insert into the todolist
            content.append(todo_entry) # XXX: This replicates the whole thing.
            content.append(para)

        node.replace_self(content)


def purge_questions(app, env, docname):
    # type: (Sphinx, BuildEnvironment, unicode) -> None
    if not hasattr(env, 'question_all_questions'):
        return
    env.question_all_questions = [todo for todo in env.question_all_questions  # type: ignore
                                  if todo['docname'] != docname]


def merge_info(app, env, docnames, other):
    # type: (Sphinx, BuildEnvironment, Iterable[unicode], BuildEnvironment) -> None
    if not hasattr(other, 'question_all_questions'):
        return
    if not hasattr(env, 'question_all_questions'):
        env.question_all_questions = []  # type: ignore
    env.question_all_questions.extend(other.question_all_questions)  # type: ignore


def visit_question_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    self.visit_admonition(node)
    # self.visit_admonition(node, 'todo')


def depart_question_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    self.depart_admonition(node)



def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_event('question-defined')
    app.add_config_value('question_include_questions', True, 'html')
    app.add_config_value('question_link_only', True, 'html')
    app.add_config_value('question_emit_warnings', False, 'html')

    app.add_node(questionlist)
    app.add_node(question_node,
                 html=(visit_question_node, depart_question_node),
                 text=(visit_question_node, depart_question_node),
                 man=(visit_question_node, depart_question_node),
                 texinfo=(visit_question_node, depart_question_node))

    app.add_directive('question', Question)
    app.add_directive('questionlist', QuestionList)
    app.connect('doctree-read', process_questions)
    app.connect('doctree-resolved', process_question_nodes)
    app.connect('env-purge-doc', purge_questions)
    app.connect('env-merge-info', merge_info)
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True
    }
