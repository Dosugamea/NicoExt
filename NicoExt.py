# coding=utf-8
import pickle
import http.client,urllib.request,urllib.parse,urllib.error,cgi,re,os,sys
import http.cookiejar
import requests
from contextlib import closing
from xml.dom import minidom
import xml.etree.ElementTree as ET
from time import sleep
import img_dl
import imp
import sys
import json
from collections import OrderedDict
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

imp.reload(sys)

NICO_URL_LOGIN = "https://secure.nicovideo.jp/secure/login?site=niconico"
write = sys.stdout.write

def g_cookie(mail,password,dir="./"):
    headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; ja; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)',
    'Accept': '*/*',
    'Accept-Language': 'ja,en-us;q=0.7,en;q=0.3',
    'Accept-Charset': 'UTF-8,*',
    'Connection': 'keep-alive',
    'Keep-Alive': '300',
    'Cookie': '; '}
    post_dict ={'show_button_facebook':'1',
    'next_url':'',
    'mail':mail,
    'password':password
    }
    headers['Referer']='https://account.nicovideo.jp/'
    headers['Content-type']='application/x-www-form-urlencoded';
    conn = http.client.HTTPSConnection('account.nicovideo.jp')
    conn.request('POST','/api/v1/login?show_button_twitter=1&site=niconico',urllib.parse.urlencode(post_dict),headers)
    rs = conn.getresponse()
    mc = re.compile('(user_session=(?!deleted)[^;]*);?').search(rs.getheader('Set-Cookie'))
    user_session = mc.group(1)
    open(dir+'nico_session.txt','w').write(user_session)
    rs.read()
    rs.close()
    conn.close()
    print("[N] "+"上手にクッキー焼けました！")

def g_comments(id,dir="./"):
    #セッションがなければ中止 あれば読み込み
    if open(dir+'nico_session.txt','r').read() == "":
        print("クッキーが見当たりませんでした！")
        sys.exit()
    headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; ja; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)',
    'Accept': '*/*',
    'Accept-Language': 'ja,en-us;q=0.7,en;q=0.3',
    'Accept-Charset': 'UTF-8,*',
    'Connection': 'keep-alive',
    'Keep-Alive': '300',
    'Cookie': open(dir+'nico_session.txt','r').read()+'; '}

    #動画情報の取得
    if id.find('sm') != -1:
        mode = 0
        videoid=id
    elif id.find('so') != -1:
        mode = 1
        html = str(urllib.request.urlopen("http://www.nicovideo.jp/watch/"+id).read())
        videoid = html[html.find('<meta itemprop="url')+60:html.find('<meta itemprop="url" content=')+70]
        print(videoid)
    elif id == "":
        mode = 1
        videoid='1397552685'
    else:
        mode = 1
        videoid=id
    got = 0
    while got == 0:
        try:
            conn = http.client.HTTPConnection('flapi.nicovideo.jp', 80)
            conn.request('GET', '/api/getflv/%s' % videoid, '', headers)
            rs = conn.getresponse()
            got = 1
        except:
            print ("Try Again...  :( ")
            sleep(2)
    body = rs.read()
    body = body.decode('utf-8')
    #print "Getflv OK"
    rs.close()
    conn.close()
    qs = cgi.parse_qs(body)
    thread_id = qs['thread_id'][0] #thread_id
    user_id = qs['user_id'][0]
    #print(thread_id , user_id)
    mc = re.compile(r'&ms=http%3A%2F%2F(.+?)\.nicovideo\.jp(%2F.+?)&').search(body)
    message_server = urllib.parse.unquote_plus(mc.group(1))
    message_path = urllib.parse.unquote_plus(mc.group(2))
    got = 0
    while got == 0:
        try:
            conn = http.client.HTTPConnection('flapi.nicovideo.jp', 80)
            conn.request('GET', '/api/getthreadkey?thread=%s' % videoid, '', headers)
            rs = conn.getresponse()
            got = 1
        except:
            print ("Try Again...  :( ")
            sleep(2)
    body = rs.read()
    rs.close()
    conn.close()
    qs = cgi.parse_qs(body)
    if mode ==1:
        thread_key = qs[b'threadkey'][0] #thread_id
        thread_key = thread_key.decode('utf-8') #Python3ではdecode必須
    if mode ==1: force_184 = "1"
    #print "Got Thread Key"
    #動画のコメント取得
    res_from=-1000 #コメントを現在から遡って何件取得してくるか
    headers['Content-type'] = 'text/xml'
    if mode ==1: postXml = '<thread thread="%s" version="%s" res_from="%s" user_id="%s" threadkey="%s" force_184="%s" scores="1"/>' % (thread_id,20090904,res_from,user_id,thread_key,force_184)
    else: postXml = '<thread thread="%s" version="%s" res_from="%s" user_id="%s" scores="1"/>' % (thread_id,20090904,res_from,user_id)
    got = 0
    while got == 0:
        try:
            conn = http.client.HTTPConnection('%s.nicovideo.jp' % message_server, 80)
            conn.request('POST', message_path, postXml, headers)
            rs = conn.getresponse()
            got = 1
        except:
            print ("Try Again...  :( ")
            sleep(2)
    body = rs.read()
    rs.close()
    conn.close()

    #ファイルに結果を保存
    f = open(dir+videoid+'_comments.xml','w',encoding='utf-8')
    f.write(body.decode('utf-8'))
    f.close()
    print("[N] "+dir+videoid+'_comments.xml'+" に保存しました")

def copy_with_progress(inp, out, size_total):
    CR = "\x0D"
    BUF_SIZE = 8192

    size = 0
    while True:
        buf = inp.read(BUF_SIZE)
        size = size + len(buf)

        if(size_total):
            write(" %s%d/%d bytes downloaded (%d%%)" % (CR, size, size_total, int(100.0*size/size_total)))
        else:
            write(" %s%d bytes downloaded" % (CR, size))
        sys.stdout.flush()

        if size == size_total : break
        out.write(buf)
    write("\n")

def nico_login(user='', passwd='', ua_ver='Mozilla/5.0 (Windows; U; Windows NT 6.1; ja; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)',dir='./'):
    URL = "http://nicovideo.jp/my/mylist"
    r = re.compile("<title>マイページ - niconico</title>")
    cj = http.cookiejar.LWPCookieJar()
    ua = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    make = 0
    #Cookieファイルがあれば読み込み、なければ作成する。    
    try:
        cj.load(dir+'nico_v_cookie.txt')
        #ちゃんとログインできたかをマイリスページを使って確認する 失敗したらMakeする
        if r.search(ua.open(URL).read()) == None:
            make = 1
    except:
        make = 1
    #必要であればクッキーを焼く
    if make == 1:
        if user == None or passwd == None:
            print("[N] !!! 再ログインが必要ですがユーザーかパスワードがないためできませんでした !!!")
            return -1
        ua.addheaders = [("User-agent", ua_ver)]
        req_body = urllib.parse.urlencode({ "next_url":"", "mail":user, "password":passwd }).encode('utf-8')
        res = ua.open(NICO_URL_LOGIN, req_body)
        res.close()
        cj.save(filename=dir+'nico_v_cookie.txt')
    return ua

def g_video(id,dir="./"):
    #ログインする。
    ua = nico_login(dir=dir)
    if ua == -1:
        print("[N] ログインに失敗したため終了します。")
        sys.exit()
    #ちょっとしたEasterEgg要素
    if id == "":
        id='1397552685'
    #動画リンクもuaで取得
    res = ua.open("http://flapi.nicovideo.jp/api/getflv/"+id)
    body = res.read().decode('utf-8')
    res.close()
    qs = cgi.parse_qs(body)
    url = qs['url'][0]
    #print ("Got directlink. / "+url)
    #視聴履歴を焼く
    res = ua.open("http://www.nicovideo.jp/watch/"+id)
    res.close()
    print("動画のダウンロードを開始します")
    info = "http://ext.nicovideo.jp/api/getthumbinfo/"+id
    html = str(urllib.request.urlopen(info).read())
    if 'status="ok"' in html:
        xmldoc = minidom.parseString(urllib.request.urlopen(info).read())
        title = xmldoc.getElementsByTagName('title')[0].firstChild.nodeValue
        f_type = xmldoc.getElementsByTagName('movie_type')[0].firstChild.nodeValue
    else:
        print ("ERROR")
        sys.exit()
    try:
        out = open(dir+id+"_"+title+"."+f_type, "wb")
    except:
        out = open(dir+id+"."+f_type, "wb")
    res = ua.open(url)
    size_total = int(res.getheader("Content-Length", None))
    copy_with_progress(res, out, size_total)
    print("ダウンロード完了")
    return title

def g_html(id,dir="./"):
    req = urllib.request.Request("http://www.nicovideo.jp/watch/"+id)
    req.add_header('Cookie',open(dir+'nico_session.txt','r').read()+';')
    resp = urllib.request.urlopen(req).read().decode('utf-8')
    rank = resp[resp.find('<li class="ranking" style="">'):resp.find('</span></li>',resp.find('<li class="ranking" style="">'))+12]
    rank = rank.replace('/ranking_graph/','http://www.nicovideo.jp/ranking_graph/')
    desc = resp[resp.find('<p class="videoDescription description">'):resp.find('<div class="videoMainInfoContainer">')]
    with open(dir+id+'_description.txt', "w", encoding='utf8') as d:
        d.write(desc)
    with open(dir+id+'_ranking.txt', "w", encoding='utf8') as r:
        r.write(rank)

def g_infos(id,dir="./"):
    url = "http://ext.nicovideo.jp/api/getthumbinfo/"+id
    html = str(urllib.request.urlopen(url).read())
    if 'status="ok"' in html:
        xmldoc = minidom.parseString(urllib.request.urlopen(url).read())
        title = xmldoc.getElementsByTagName('title')[0].firstChild.nodeValue
        thumburl = xmldoc.getElementsByTagName('thumbnail_url')[0].firstChild.nodeValue
        print (thumburl)
        sleep(1)
        if 'sm' in url:
            iconurl = xmldoc.getElementsByTagName('user_icon_url')[0].firstChild.nodeValue
            got = 0
            while got == 0:
                try:
                    thumb_large = img_dl.download_image(thumburl+".L",timeout=300)
                    got = 1
                except:
                    print("L_thumbの取得に失敗しました 3秒後リトライします...")
                    sleep(3)
            if thumb_large != "ERROR":
                img_dl.save_image(dir+id + "_thumb_large.jpg",thumb_large)
        else:
            iconurl = xmldoc.getElementsByTagName('ch_icon_url')[0].firstChild.nodeValue
        print("[N] "+"L_Thumbを取得しました")
        sleep(1)
        got = 0
        while got == 0:
                try:
                    img_dl.save_image(dir+id + "_thumb.jpg",img_dl.download_image(thumburl,timeout=300))
                    got = 1
                except:
                    print("Thumbの取得に失敗しました 3秒後リトライします...")
                    sleep(3)
        print("[N] "+"Thumbを取得しました")
        sleep(1)
        got = 0
        while got == 0:
                try:
                    img_dl.save_image(dir+id + "_user_icon.jpg",img_dl.download_image(iconurl,timeout=300))
                    got = 1
                except:
                    print("User_iconの取得に失敗しました 3秒後リトライします...")
                    sleep(3)
        print("[N] "+"ユーザーアイコンを取得しました")
        sleep(1)
        urllib.request.urlretrieve(url,"{0}".format(dir+id+"_info.xml"))
        print("[N] "+"Thumbinfoを取得しました")
        decoder = json.JSONDecoder(object_pairs_hook=OrderedDict)
        js = OrderedDict()
        req = urllib.request.Request("http://www.nicovideo.jp/watch/"+id)
        req.add_header('Cookie',open(dir+'nico_session.txt','r').read()+';')
        resp = urllib.request.urlopen(req).read().decode('utf-8')
        js["VideoPostedAt"] = resp[resp.find('<span class="videoPostedAt">')+28:resp.find('</span>',resp.find('<span class="videoPostedAt">'))]
        js["viewCount"] = resp[resp.find('<span class="viewCount">')+24:resp.find('</span>',resp.find('<span class="viewCount">'))]
        js["commentCount"] = resp[resp.find('<span class="commentCount">')+27:resp.find('</span>',resp.find('<span class="commentCount">'))]
        js["mylistCount"] = resp[resp.find('<span class="mylistCount">')+26:resp.find('</span>',resp.find('<span class="mylistCount">'))]
        js["categoryName"] = resp[resp.find('<span class="categoryName">')+27:resp.find('</span>',resp.find('<span class="categoryName">'))]
        if 'カテゴリ前日総合順位:<span class="yesterdayRank"><span class="rank_word_postfix" style="display:none;"><span class="rank"></span>位</span><span class="no_rank_word" style="">' in resp:
	        js["yesterdayRank"] = "圏外"
        else:
	        js["yesterdayRank"] = resp[resp.find('カテゴリ前日総合順位:<span class="yesterdayRank"><span class="rank_word_postfix" style=""><span class="rank">')+99:resp.find('</span>',resp.find('カテゴリ前日総合順位:<span class="yesterdayRank"><span class="rank_word_postfix" style=""><span class="rank">'))]
        if '過去最高:<span class="rank_word_postfix" style="display:none;"><span class="rank"></span>' in resp:
	        js["bestRank"] = "圏外"
        else:
	        js["bestRank"] = resp[resp.find('過去最高:<span class="rank_word_postfix" style=""><span class="rank">')+65:resp.find('</span>',resp.find('過去最高:<span class="rank_word_postfix" style=""><span class="rank">'))]
        js["VideoDescription"] = resp[resp.find('<p class="videoDescription description">'):resp.find('<div class="videoMainInfoContainer">')]
        print("[N] "+"動画情報を取得しました")
        url = "http://ichiba.nicovideo.jp/embed/zero/show_ichiba?v="+id
        ichiba_body = str(urllib.request.urlopen(url).read().decode('unicode_escape'))
        ichiba_body = ichiba_body.replace("\\","").replace("／","").replace("&nbsp;","").replace("    ","").replace('{"pickup":"',"").replace('"main":"',"").replace("…","...").replace('",',"")
        ichiba_body = ichiba_body[:ichiba_body.rfind("</div>")+6]
        js["ichiba"] = OrderedDict([])
        if '商品のタグをここに表示することができます' not in ichiba_body:
            pickup_id = -1
            pickup_img_url = -1
            pickup_title = -1
            pickup_buy = -1
            pickup_id = ichiba_body[ichiba_body.find("ichiba.click('")+14:ichiba_body.find("');",ichiba_body.find("ichiba.click('")):]
            pickup_img_url = ichiba_body[ichiba_body.find('<span id="pickup_mq" style="width:210px;"></span>\n<img src=')+60:ichiba_body.find('" w',ichiba_body.find('<span id="pickup_mq" style="width:210px;"></span>\n<img src='))]
            pickup_title = ichiba_body[ichiba_body.find('title',ichiba_body.find('<span id="pickup_mq" style="width:210px;"></span>\n<img src='))+7:ichiba_body.find('" alt="',ichiba_body.find('" w',ichiba_body.find('<span id="pickup_mq" style="width:210px;"></span>\n<img src=')))]
            pickup_buy = ichiba_body[ichiba_body.find('<span class="buy">')+18:ichiba_body.find('</span>',ichiba_body.find('<span class="buy">'))]

            items_id = []
            items_buy_url = []
            items_img_url = []
            items_title = []
            items_maker = []
            items_click = []
            items_click_invideo = []
            items_price = []
            items_buy = []  
            search = 0
            search2 = 0
            search4 = ichiba_body.find('<dl class="ichiba_mainitem">')

            for i in range(0,ichiba_body.count('ichibaitem_watch_')):
                search = ichiba_body.find('<div id="ichibaitem_watch_',search)+26
                search2 = ichiba_body.find('<a style="cursor:pointer;" href="',search2)+33
                search3 = ichiba_body.find('<img src="',search2)+10
                search4 = ichiba_body.find('title=',search4)+7
                search5 = ichiba_body.find('<dd class="maker">',search4)+18
                chk = ichiba_body[ichiba_body.find('<dd class="action">',search):ichiba_body.find('</dd>',ichiba_body.find('<dd class="action">',search))]
                chk2 = ichiba_body[search5:ichiba_body.find('</dd>',search5)+100] 
                items_id.append(ichiba_body[search:ichiba_body.find('">',search)])
                items_buy_url.append(ichiba_body[search2:ichiba_body.find('" class=',search2)])
                items_img_url.append(ichiba_body[search3:ichiba_body.find('" ',search3)])
                items_title.append(ichiba_body[search4:ichiba_body.find('" ',search4)])
                items_maker.append(ichiba_body[search5:ichiba_body.find('</dd>',search5)])
                if 'buy' in chk:
                    items_buy.append(chk[chk.find('<span class="buy">')+18:chk.find('</span>',chk.find('<span class="buy">'))])
                else:
                    items_buy.append('none')
                if 'click' in chk:
                    items_click.append(chk[chk.find('<span class="click">')+20:chk.find('</span>',chk.find('<span class="click">'))])
                    if '（この動画で' in chk:
                        items_click_invideo.append(chk[chk.find('<span>',)+6:chk.find('</span>',chk.find('<span>'))])
                    else:
                        items_click_invideo.append('none')
                else:
                    items_click.append('none')
                    items_click_invideo.append('none')
                if 'price' in chk2:
                    if '% off )' in chk2:
                        items_price.append(chk2[chk2.find('<dd class="price">')+18:chk2.find(')</span')+1].replace('<span>',''))
                    else:
                        items_price.append(chk2[chk2.find('<dd class="price">')+18:chk2.find('</dd>',chk2.find('<dd class="price">')+18)])
                else:
                    items_price.append('none')
            for i in range(0,len(items_title)):
                js["ichiba"][items_id[i]] = OrderedDict([])
                js["ichiba"][items_id[i]]["title"] = items_title[i]
                js["ichiba"][items_id[i]]["maker"] = items_maker[i]
                js["ichiba"][items_id[i]]["buy_url"] = items_buy_url[i]
                js["ichiba"][items_id[i]]["img_url"] = items_img_url[i]
                js["ichiba"][items_id[i]]["click"] = items_click[i]
                js["ichiba"][items_id[i]]["click_invideo"] = items_click_invideo[i]
                js["ichiba"][items_id[i]]["buy"] = items_buy[i]
                js["ichiba"][items_id[i]]["price"] = items_price[i]
        else:
            js["ichiba"] = "none"
        js["relations"] = OrderedDict([])
        js["relations"]["related"] = OrderedDict([])
        js["relations"]["recommend"] = OrderedDict([])
        print("[N] "+"市場情報を取得しました")
        #まずアクセスしてrelatedかどうか確認する
        url = "http://flapi.nicovideo.jp/api/getrelation?page=1&video="+id
        relations = str(urllib.request.urlopen(url).read().decode('utf8'))
        root = ET.fromstring(relations)
        total = int(root[0].text)
        pages = int(root[1].text)
        count = int(root[2].text)
        type = root[3].text
        #print ("type "+str(type))
        #print ("pages: "+str(pages))
        #print ("items total: "+str(total))
        pid = 1
        cid = 1
        st = 4
        #次にそれがrelatedであれば最終ページ+1ページ目の個数を取得して recommendを入手する
        if type == "related":
            url = "http://flapi.nicovideo.jp/api/getrelation?video="+id+"&order=d&page="+str(int(root[1].text)+1)
            relations = str(urllib.request.urlopen(url).read().decode('utf8'))
            root = ET.fromstring(relations)
            minus = int(root[2].text)
            count = int(root[2].text)
            #途中で関連動画数が変化するのであてにならない
            #print ("recommend_items: "+str(minus))
            #print ("related_items: "+str(total-minus))

        #(ここでついでにrecommendの内容もいれる)
        for i in range(0,count):
            js["relations"]["recommend"][cid] = OrderedDict([])
            js["relations"]["recommend"][cid]["url"] = root[st][0].text
            js["relations"]["recommend"][cid]["thumbnail"] = root[st][1].text
            js["relations"]["recommend"][cid]["title"] = root[st][2].text
            js["relations"]["recommend"][cid]["view"] = root[st][3].text
            js["relations"]["recommend"][cid]["comment"] = root[st][4].text
            js["relations"]["recommend"][cid]["mylist"] = root[st][5].text
            js["relations"]["recommend"][cid]["length"] = root[st][6].text
            js["relations"]["recommend"][cid]["time"] = root[st][7].text
            st+=1
            cid+=1
        #数を元に戻してから
        cid = 1
        st = 4
        #relatedだったなら 
        if type == "related" and pages > 1:
            for pid in range(1,pages):
                url = "http://flapi.nicovideo.jp/api/getrelation?video="+id+"&order=d&page="+str(pid+1)
                relations = str(urllib.request.urlopen(url).read().decode('utf8'))
                root = ET.fromstring(relations)
                count = int(root[2].text)
                #print(str(pid)+"/"+str(count)+"/"+str(root[3].text))
                st = 4
                #たまに途中でタイプが変わるので変わってしまったらそのときはスルーする
                if root[3].text == "related":
                    for i in range(0,count):
                            js["relations"]["related"][cid] = OrderedDict([])
                            js["relations"]["related"][cid]["url"] = root[st][0].text
                            js["relations"]["related"][cid]["thumbnail"] = root[st][1].text
                            js["relations"]["related"][cid]["title"] = root[st][2].text
                            js["relations"]["related"][cid]["view"] = root[st][3].text
                            js["relations"]["related"][cid]["comment"] = root[st][4].text
                            js["relations"]["related"][cid]["mylist"] = root[st][5].text
                            js["relations"]["related"][cid]["length"] = root[st][6].text
                            js["relations"]["related"][cid]["time"] = root[st][7].text
                            cid+=1
                            st+=1
                else:
                    print("Type Error: ページの途中で型が変わりました")
        elif type == "related" and pages == 1:
            #url = "http://flapi.nicovideo.jp/api/getrelation?video="+id+"&order=d&page=1"
            #relations = str(urllib.request.urlopen(url).read().decode('utf8'))
            #root = ET.fromstring(relations)
            count = int(root[2].text)
            #print("1"+"/"+str(count)+"/"+str(root[3].text))
            st = 4
            if root[3].text == "related":
                for i in range(0,count):
                        js["relations"]["related"][cid] = OrderedDict([])
                        js["relations"]["related"][cid]["url"] = root[st][0].text
                        js["relations"]["related"][cid]["thumbnail"] = root[st][1].text
                        js["relations"]["related"][cid]["title"] = root[st][2].text
                        js["relations"]["related"][cid]["view"] = root[st][3].text
                        js["relations"]["related"][cid]["comment"] = root[st][4].text
                        js["relations"]["related"][cid]["mylist"] = root[st][5].text
                        js["relations"]["related"][cid]["length"] = root[st][6].text
                        js["relations"]["related"][cid]["time"] = root[st][7].text
                        cid+=1
                        st+=1
            else:
                print("Type Error: Relatedの取得に失敗しました")
        print("[N] "+"関連動画情報を取得しました")
        id2 = id
        if "sm" not in id and "so" not in id:
            thumbinfo = urllib.request.urlopen("http://ext.nicovideo.jp/api/getthumbinfo/"+id).read()
            xmldoc = minidom.parseString(thumbinfo)
            id2 = xmldoc.getElementsByTagName('video_id')[0].firstChild.nodeValue
        url = "http://api.uad.nicovideo.jp/UadsVideoService/getAdvertisingJsonp?callback=jsonp&videoid="+id2
        koukoku = str(urllib.request.urlopen(url).read().decode('utf8'))
        koukoku = json.loads(koukoku.split("([")[1].split("]);")[0])
        js["koukoku"] = OrderedDict([])
        js["koukoku"]["points"] = koukoku["total"]
        js["koukoku"]["level"] = koukoku["level"]
        print("[N] "+"広告情報を取得しました")
        with open(dir+id+"_videoinfos.json", "w", encoding='utf8') as f:
            json.dump(js, f, ensure_ascii=False, indent=4,separators=(',', ': '))
        print("[N] "+"取得したデータを保存しました")
    elif '<code>DELETED</code>' in html:
        print("[N] "+id+" は削除されています。")
    elif '<code>NOT_FOUND</code>' in html:
        print("[N] "+id+" は存在しません。")
    else:
        print("[N] "+"例外が発生しました")

def g_all(id,dir='./dir'):
    g_comments(id)
    g_video(id)
    g_infos(id)
		
if __name__ == "__main__":
    print("Help:")
    print("      g_cookie(mail,password):")
    print("               クッキーを焼きます")
    print("      g_video(id):")
    print("               動画をダウンロードします")
    print("      g_comments(id):")
    print("               コメントをダウンロードします")
    print("      g_infos(id):")
    print("               thumbinfo関連をダウンロードします")
