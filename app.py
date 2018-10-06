from datetime import datetime, timezone

from jinja2 import Markup, escape
from flask import Flask, Response, render_template, request, jsonify

import api

app = Flask(__name__)

stalker = api.NSASimulator()

def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

@app.route('/')
def index():
    profiles = stalker.get_profiles()
    return Response(stream_template("main.html", profiles=profiles,
        friends=stalker.friends, interests=stalker.get_interests()))

@app.route('/recs')
def recs():
    profiles = stalker.get_recs()
    return render_template("main.html", profiles=profiles,
        friends=stalker.friends, interests=stalker.get_interests())

@app.route('/user/<user_id>')
def user(user_id):
    profiles = [stalker.get_user(user_id)]
    return render_template("main.html", profiles=profiles,
        friends=stalker.friends, interests=stalker.get_interests())

@app.route('/user/<user_id>/superlike')
def superlike(user_id):
    r = stalker._post('like/%s/super' % user_id)
    return jsonify(r.json()), r.status_code

@app.route('/api/<path:path>')
def api_call(path):
    r = stalker._get(path, params=request.args)
    return jsonify(r.json()), r.status_code

@app.route('/token')
def token():
    # idk
    return stalker.headers['X-Auth-Token']

@app.route('/app-version')
def get_app_version():
    return stalker.headers.get('app-version')

@app.route('/change-app-version')
def change_app_version():
    # yeah idk what I'm doing
    old = stalker.headers.get('app-version')
    if 'v' in request.args:
        stalker.headers['app-version'] = request.args['v']
    else:
        del stalker.headers['app-version']
    return old

@app.template_filter()
def nl2br(value):
    result = '<br />\n'.join([escape(x) for x in value.splitlines()])
    return Markup(result)

@app.template_filter()
def humandate(value):
    return value.strftime("%b %d %Y %H:%M:%S")

@app.template_filter()
def yearssince(value):
    # replacing year in fuzzy birthdates with current year always is in future
    return datetime.now(timezone.utc).year - value.year - 1
    # delta = datetime.now(timezone.utc) - value
    # return delta.days // 365

@app.template_filter()
def pagemagic(value):
    result = escape(value['name'])
    if 'id' in value:
        result = '<a href="https://www.facebook.com/%s">%s</a>' % (value['id'], result)
    return Markup(result)

if __name__ == '__main__':
    app.run(debug=True)
