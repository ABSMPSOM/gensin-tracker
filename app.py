from flask import Flask, render_template, request, redirect, url_for
from scraper import GenshinQuestScraper

app = Flask(__name__)
scraper = GenshinQuestScraper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quest', methods=['GET'])
def quest():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('index'))
        
    quest_data = scraper.fetch_quest_data(query)
    
    if "error" in quest_data:
        return render_template('index.html', error=quest_data["error"], query=query)
        
    return render_template('quest.html', data=quest_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)