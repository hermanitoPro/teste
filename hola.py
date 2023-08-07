import os #biblioteca de manipulação de funções do S.O
from slack_bolt import App #Classe da biblioteca que manipula funções do app slack
from slack_bolt.adapter.socket_mode import SocketModeHandler # Classe da biblioteca que manipula slack usado em socket mode
from blue.biblioteca.inteliblue import ChatterBlue #Classe onde está a parte de busca de perguntas X respostas (atenção: biblioteca InteliBlue é de propriedade Neon, não é uma biblioteca pública)
import random #biblioteca de randomização
from blue.biblioteca.bluedata import listMessage, listAction,listMessageNotFound, listMessageEnd, listMessageRandom, findAction, listUser,listSubcategorySN,listBusinessServiceSN #biblioteca de busca de perguntas e respostas na base sql
from blue.biblioteca.bluereport import attendRegister, attendNoSuccess, attendSuccess,questionNotFound, attendanceRedirected , timeBalance, attendanceGec , hierarchyPeopleAnalytics# biblioteca de registro de atendimentos no mongo
from blue.biblioteca.bluesn import openRequest, findIncident,findChangeReq # biblioteca de integração com o service now
import requests
import io
import json #biblioteca de manipulação de arquivos json
import csv
import pandas as pd
from datetime import datetime, timedelta #biblioteca de data e hora
from blue.biblioteca.conectaBase import MongoDB
import time


cwd=os.getcwd()

print('Carregando informações...')


lstMsg = listMessage() #instância da classe mensagens
linhas = lstMsg.get() #chamada do método de leitura da base de perguntas e respostas

lstAct = listAction()#instância da classe de ações
linhas_action=lstAct.get() #chamada do método de leitura da base de ações e botões que vão aparecer

lstMsgNotFound=listMessageNotFound() #instância da classe de mensagem de retorno para perguntas não encontradas
linhas_notfound=lstMsgNotFound.get() #chamada do método de leitura da base de ações e botões que vão aparecer

lstMsgEnd=listMessageEnd() #instância da classe de mensagem de finalização de atendimento
linhas_end=lstMsgEnd.get() #chamada do método de leitura da base de mensagem de final de atendimento

lstMsgRan=listMessageRandom() #instância da classe de mensagens randomizadas
linhas_random=lstMsgRan.get() #chamada do método de leitura da base de mensagens randômicas
fndAct=findAction()

lstUser=listUser() #instância da classe de mensagem de finalização de atendimento
linhas_user=lstUser.get() #chamada do método de leitura da base de mensagem de final de atendimento

lstSubcat=listSubcategorySN() #instância da classe de mensagem de finalização de atendimento

lstBusSrvSN=listBusinessServiceSN() #instância da classe de mensagem de finalização de atendimento

opnReq=openRequest() #instância da classe de integração com o service now, método de abertura de chamado
fndInc=findIncident() #instância da classe de integração com o service now, método de busca de incidentes
fndChgReq=findChangeReq() #instância da classe de integração com o service now, método de busca de mudanças

rdAttendRegister= attendRegister()#instância da classe de registro de atendimentos
rdAttendNoSuccess= attendNoSuccess()#instância da classe de registro de atendimentos sem sucesso
rdAttendSuccess=attendSuccess()#instância da classe  de registro de atendimentos com sucesso
rdQuestionNotFound=questionNotFound()#instância da classe  de registro de perguntas não encontradas
rdAttendanceRedirected=attendanceRedirected()#instância da classe  de registro de atendimentos redirecionados
rdTimeBalance=timeBalance()#instância da classe  de registro de atendimentos redirecionados
rdAttendanceGec=attendanceGec()#instância da classe  de registro de atendimentos redirecionados
rdHierarchyPeopleAnalytics=hierarchyPeopleAnalytics()#instancia da clase de Relatorios de People analyts


for key, reg in linhas_notfound.items():
    msg_notfound=reg[0] #busca da mensagem que será enviada quando a Blue não encontrar a pergunta

aleat_lst=[]
for key, reg in linhas_random.items():
    aleat_lst.append(reg[0]) #Monta lista de mensagens aleatórias
    
for key, reg in linhas_end.items():
    msg_end=reg[0] #busca da mensagem que será enviada quando a Blue não encontrar a pergunta

#carrega lista de perguntas e respostas
cb=ChatterBlue()
quest=cb.set_load(linhas) # chama a função set_load para carregar as perguntas e o id para uma lista 

# cria o objeto app com o token do bot
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
assunto=''

data_atual=''
dic={}

# Metodo Obter data e restar para calcular o restante do mes
today = datetime.today().date()
first_day_next_month = datetime(today.year, today.month % 12 + 1, 1).date()
end_date = first_day_next_month - timedelta(days=1)
days_left = (end_date - today).days



class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r
        
@app.event("message")
@app.event("file_created")        
        

@app.message("") #disparado na recepção de msg
@app.action("acoes") # disparado na recepção de actions


       
#Trata mensagens recebidas e dá a resposta
def message_hello(message, client,action, event,body,ack,logger):
    ack()
    logger.info(body)
    pergunta=''
    user_id=''
    channel_id=''
    thread=''
    user_nm=''
    #alimentação de variáveis com as constantes vindas do json retornado a cada interação do usuário
    global assunto
    global data_atual
    global dic
    global pergunta_id
    global find_sn
    if data_atual!=datetime.today().strftime('%Y-%m-%d'):
        for conv in client.conversations_list(types="im"): #percorre a lista de canais 
            for canal in conv['channels']:
                dic[canal["user"]]=[canal['id']]
        with open(cwd + '/canais.json','w') as arq_json:
            json.dump(dic,arq_json)
        data_atual=datetime.today().strftime('%Y-%m-%d')
    #Banco de horas
    try: 
        if event['subtype']!=None and message['channel'][0]!='C':
            user_id=message['user']
            channel_id=message['channel']
            thread=message['ts']
            user_email=client.users_info(token=os.environ.get("SLACK_BOT_TOKEN"),user=user_id)['user']['profile']['email']
            user_nm_arr=user_email.split('@')
            user_nm=user_nm_arr[0]
            nm_arquivo=message['files'][0]['name']
            envia_bh=0
            atendimento_gec=0
            people_hierarquia=0
            retorno=rdTimeBalance.delete()
            retorno=rdAttendanceGec.delete()
            retorno=rdHierarchyPeopleAnalytics.delete()
            #linhas_user=lstUser.get() 
            for key, reg in linhas_user.items():
                if str(reg[0]).lower()=='upload banco de horas' and str(reg[2]).lower()==str(user_nm).lower() and str(reg[1]).lower()==str(nm_arquivo).lower():
                    envia_bh=1
                elif  str(reg[0]).lower()=='Upload Atendimento GEC'.lower() and str(reg[2]).lower()==str(user_nm).lower() and str(reg[1]).lower()==str(nm_arquivo).lower():
                    atendimento_gec=1
                elif  str(reg[0]).lower()=='Upload Hierarquia Neon'.lower() and str(reg[2]).lower()==str(user_nm).lower() and str(reg[1]).lower()==str(nm_arquivo).lower():
                    people_hierarquia=1     
            if envia_bh==1:                
                result=client.chat_postMessage(channel=channel_id,text='Aguarde...',thread_ts=thread)
                result=client.chat_postMessage(channel=channel_id,text='Capturando canais..',thread_ts=thread)                
                result=client.chat_postMessage(channel=channel_id,text='Lendo arquivo de entrada..',thread_ts=thread)  
                for i in event['files']:
                    if i['url_private_download'] and i['mode']=='snippet':    
                        url=i['url_private']
                        token=os.environ["SLACK_BOT_TOKEN"]
                        r = requests.get(url, auth=BearerAuth(token))
                        file_data = r.content   # get binary content
                        file_name="banco.csv"
                        # save file to disk
                        with open(file_name , 'w+b') as f:
                            f.write(bytearray(file_data))         
                result=client.chat_postMessage(channel=channel_id,text='Separando informações por gestor..',thread_ts=thread)    
                caminho=cwd + '/banco.csv'
                df=pd.read_csv(caminho,sep=';')                                
                df = df.astype(str)  
                for i, row in df.iterrows():
                    e_mail=(row['E-mail Gestor']).lower()
                    try:
                        id_usu=client.users_lookupByEmail(token=os.environ.get("SLACK_BOT_TOKEN"),email=e_mail)['user']['id']                        
                        time.sleep(1)
                        canal_gestor=dic.get(id_usu)                        
                        if canal_gestor!='None':
                            bancohoras=rdTimeBalance.post(
                                empNm=(row['Nome']),
                                empEmail=(row['E-mail Profissional']),
                                managerNm=(row['Nome do Gestor']),
                                managerEmail=(row['E-mail Gestor']),
                                hourQt=(row['Banco Total']),
                                channelId=canal_gestor[0],
                                pendencyNm=(row['Pendencias']))             
                    except Exception as e:
                        print(e)
                        verifica_bh='e-mail não existe'
                document=rdTimeBalance.get()
                df=pd.DataFrame(document)
                df_grp=df.groupby(["CHANNEL_ID"]).size().reset_index(name='count')
            
                result=client.chat_postMessage(channel=channel_id,text='Enviando para gestores..',thread_ts=thread)
                for i in df_grp.index:
                    filtra_gestor=df[df['CHANNEL_ID'] == str(df_grp['CHANNEL_ID'][i])]
                    filtra_gestor.pop("CHANNEL_ID")
                    filtra_gestor.pop("_id")
                    filtra_indx=filtra_gestor.set_index('EMPLOYEE_NM')
                    filtra_indx.to_excel(r'Banco_de_Horas.xlsx')
                    arq= cwd + "/Banco_de_Horas.xlsx"
                    try:
                        result=client.files_upload(channels=str(df_grp['CHANNEL_ID'][i]),initial_comment= f":alarm_clock::hourglass: BANCO DE HORAS: FECHAMENTO DO QUADRIMESTRE :alarm_clock::hourglass: \n\nOiê, Líder! Tudo azul por aí? \n\nNo dia 31 de agosto, vai rolar o fechamento do quadrimestre e faltam poucos dias para o seu time conseguir compensar o banco de horas atual.Tá lembrada(o)? :thinking_face: \n\nO equilíbrio saudável de banco de horas é uma ação fundamental para a eficiência organizacional da Neon e também para o bem-estar de seu time. :dart: \n\nPra te ajudar nessa, estou enviando o relatório com o saldo atual do BH da sua galera! Agora é só combinar aquela folguinha marota pra(o) Neowner recarregar as energias.:blue_heart::catjam: \n \nVale lembrar que para esse saldo estar correto, é necessário que o Neowner esteja em dia com o controle de horas no sistema, sem pendências. :eyes:\n \nConto muito com você! Beijinhos da Blue. :blue_nova: \n \n*#Faltam {days_left} Dias*! :confia-e-brilha:",file=arq)
                        time.sleep(1)
                    except Exception as e:
                        print(e)
                        result=client.files_upload(channels=str(channel_id),initial_comment='Canal do gestor não localizado',file=arq)
                        time.sleep(1)                
                os.remove(cwd + "/Banco_de_Horas.xlsx")
                os.remove(cwd + "/banco.csv")                 
                result=client.chat_postMessage(channel=channel_id,text='Envio realizado',thread_ts=thread)
            #Atendimento Gec 
            elif atendimento_gec==1:
                    result=client.chat_postMessage(channel=channel_id,text='Aguarde...',thread_ts=thread)
                    result=client.chat_postMessage(channel=channel_id,text='Capturando canais..',thread_ts=thread)                
                    result=client.chat_postMessage(channel=channel_id,text='Lendo arquivo de entrada..',thread_ts=thread)                
                    for i in event['files']:
                        if i['url_private_download'] and i['mode']=='snippet':    
                            url=i['url_private']
                            token=os.environ["SLACK_BOT_TOKEN"]
                            r = requests.get(url, auth=BearerAuth(token))
                            file_data = r.content   # get binary content
                            file_name="atendimento_gec.csv"
                            # save file to disk
                            with open(file_name , 'w+b') as f:
                                f.write(bytearray(file_data))
                    result=client.chat_postMessage(channel=channel_id,text='Separando os atendimentos por gestor..',thread_ts=thread)    
                    caminho=cwd + '/atendimento_gec.csv'
                    df=pd.read_csv(caminho,sep=';')
                    for i in df.index:
                        e_mail=str(df['E-mail Gestor'][i]).lower()
                        try:
                            id_usu=client.users_lookupByEmail(token=os.environ.get("SLACK_BOT_TOKEN"),email=e_mail)['user']['id']  
                            time.sleep(4)
                            canal_gestor=dic.get(id_usu)
                            if canal_gestor!='None':
                                atendimentogec=rdAttendanceGec.post(str(df['Nome'][i]),str(df['E-mail Profissional'][i]),str(df['Nome do Gestor'][i]),str(df['E-mail Gestor'][i]),str(df['Conversation'][i]),str(df['TMO Interação'][i]),str(df['Skill'][i]),str(canal_gestor).replace("[","").replace("]","").replace("'",""))
                        except Exception as e:
                            print(e)
                            verifica_atendimento='e-mail não existe'
                    document=rdAttendanceGec.get()
                    df=pd.DataFrame(document)
                    df_grp=df.groupby(["CHANNEL_ID"]).size().reset_index(name='count')                    
                    result=client.chat_postMessage(channel=channel_id,text='Enviando para gestores..',thread_ts=thread)
                    for i in df_grp.index:
                        filtra_gestor=df[df['CHANNEL_ID'] == str(df_grp['CHANNEL_ID'][i])]
                        filtra_gestor.pop("CHANNEL_ID")
                        filtra_gestor.pop("_id")
                        filtra_indx=filtra_gestor.set_index('EMPLOYEE_NM')
                        filtra_indx.to_excel(r'Atendimento_Gec.xlsx')
                        arq= cwd + "/Atendimento_Gec.xlsx"
                        try:
                            result=client.files_upload(channels=str(df_grp['CHANNEL_ID'][i]),initial_comment=':plantaoo::blue_nova: PLANTÃO DA BLUE :plantaoo::blue_nova: \n \nHello! \n \nPassando rapidinho pra dizer que tem cliente esperando resposta já faz um tempinho! :slightly_smiling_face: \n \nSei que tá bem corrido, mas não podemos deixar de cuidar da experiência da Neonzada, não é mesmo? :blue_heart: \n \nBora nessa, eu sei bem que com esse time incrível não tempo ruim. :foguete-neon: \n \nBeijinhos da Blue!',file=arq)
                            time.sleep(1)
                        except Exception as e:
                            print(e)
                            result=client.files_upload(channels=str(channel_id),initial_comment='Canal do gestor não localizado',file=arq)
                            time.sleep(1)
                    os.remove(cwd + "/Atendimento_Gec.xlsx")
                    os.remove(cwd + "/atendimento_gec.csv")
                    
                    result=client.chat_postMessage(channel=channel_id,text='Envio realizado',thread_ts=thread)
                    
            #People analyts        
            elif people_hierarquia==1:
                result=client.chat_postMessage(channel=channel_id,text='Aguarde...',thread_ts=thread)
                result=client.chat_postMessage(channel=channel_id,text='Capturando canais..',thread_ts=thread)                
                result=client.chat_postMessage(channel=channel_id,text='Lendo arquivo de entrada..',thread_ts=thread) 
                for i in event['files']:
                    if i['url_private_download'] and i['mode']=='snippet':    
                        url=i['url_private']
                        token=os.environ["SLACK_BOT_TOKEN"]
                        r = requests.get(url, auth=BearerAuth(token))
                        file_data = r.content   # get binary content
                        print(file_data)
                        file_name=" "
                        # save file to disk
                        with open(os.path.join(cwd, 'hierarquia.csv') , 'w+b') as f:
                            f.write(bytearray(file_data))
                result=client.chat_postMessage(channel=channel_id,text='Separando os atendimentos por gestor..',thread_ts=thread)    
                caminho=os.path.join(cwd, 'hierarquia.csv')
                df=pd.read_csv(caminho,sep=';') 
                df = df.astype(str)                  
                for i, row in df.iterrows():
                    e_mail=(row['Destinatário'][i]).lower()
                    try:
                        id_usu=client.users_lookupByEmail(token=os.environ.get("SLACK_BOT_TOKEN"),email=e_mail)['user']['id']
                        time.sleep(1)
                        canal_gestor=dic.get(id_usu)
                        if canal_gestor!='None':
                            peopleHerarquia=rdHierarchyPeopleAnalytics.post(
                                empNm=(row['Nome Funcionário/Vaga']),
                                macroAreaNm=(row['Macro Área']),
                                areaNm=(row['Área']),
                                empEmail=(row['Email']),
                                managerEmail=(row['Nome Gestor']),
                                costCenterNm=(row['CC']),
                                bussinessNm=(row['BU']),
                                tribeNM=(row['Tribo']),
                                squadNm=(row['Squad']),
                                bussinessNm2=(row['BU_2']),
                                tribeNM2=(row['Tribo_2']),
                                squadNm2=(row['Squad_2']),
                                managerNm0=(row['Nome_N0']),
                                managerNm01=(row['Nome_N1']),
                                managerNm02=(row['Nome_N2']),
                                managerNm03=(row['Nome_N3']),
                                managerNm04=(row['Nome_N4']),
                                managerNm05=(row['Nome_N5']),
                                managerNm06=(row['Nome_N6']),
                                managerNm07=(row['Nome_N7']),
                                areNM1=(row['AREA_1']),
                                areNM2=(row['AREA_2']),
                                areNM3=(row['AREA_3']),
                                areNM4=(row['AREA_4']),
                                areNM5=(row['AREA_5']),
                                areNM6=(row['AREA_6']),
                                areNM7=(row['AREA_7']),
                                destinationEmail=(row['Destinatário']),
                                channelId=canal_gestor[0])                                                 
                    except Exception as e:
                        print(e)
                        verifica_hierarquia='e-mail não existe'
                document=rdHierarchyPeopleAnalytics.get()
                df=pd.DataFrame(document)
                df_grp=df.groupby(["CHANNEL_ID"]).size().reset_index(name='count')

                result=client.chat_postMessage(channel=channel_id,text='Enviando para gestores..',thread_ts=thread)
                for i in df_grp.index:
                    filtra_gestor=df[df['CHANNEL_ID'] == str(df_grp['CHANNEL_ID'][i])]
                    filtra_gestor.pop("CHANNEL_ID")
                    filtra_gestor.pop("_id")
                    filtra_indx=filtra_gestor.set_index('EMPLOYEE_NM')
                    filtra_indx.to_excel(r'People_Hierarquia.xlsx')
                    arq= cwd + "/People_Hierarquia.xlsx"
                    
                    try:
                        result=client.files_upload(channels=str(df_grp['CHANNEL_ID'][i]),initial_comment='Oiê, Líder! Tudo Blue por aí?\n\nTem um tempinho que chamei você pra contar sobre o envio automático do relatório da estrutura do seu time. Lembra? :hoho: \n\nMuito que bem, hoje, tô passando rapidinho pra pedir pra você dar uma olhada no Organimi e no relatório pra ver se está tudo certo.\n\nSe tiver alguma coisa errada, basta acessar esse :point_right::skin-tone-5: <https://app.pipefy.com/public/form/dleztT2T|link aqui> :point_left::skin-tone-5: e solicitar as alterações.\n\n>Ah, antes que eu me esqueça, vale lembrar alguns pontos:\n>●Através do link você pode solicitar alterações para o perímetro ágil e hierárquico;\n>●Alterações na estrutura hierárquica precisam ser validadas pelo time de BPs;\n>●Todos os sistemas, inclusive a apuração de resultados para o P4P, usam nossa estrutura como base. Por isso, é importante que esses dados estejam atualizados.\n\nCaso tenha alguma duvida entre em contato direto com as(os) BPs do seu time.\n\nValeuuu! Beijinhos da Blue! :smiling_face_with_3_hearts: (editado)',file=arq)
                        time.sleep(1)
                    except Exception as e:
                        print(e)
                        result=client.files_upload(channels=str(channel_id),initial_comment='Canal do gestor não localizado',file=arq)
                        time.sleep(1)
                os.remove(cwd + "/People_Hierarquia.xlsx")
                os.remove(cwd + "/hierarquia.csv")
                    
                result=client.chat_postMessage(channel=channel_id,text='Envio realizado',thread_ts=thread)        
            else:
                result=client.chat_postMessage(channel=channel_id,text='Você não tem permissão para realizar essa ação',thread_ts=thread)
    except Exception as e:
            print(e)
      
            if message!=None and message['channel'][0]!='C': #verifica se o acionamento não veio de um canal 
                channel_id=message['channel']
                thread=message['ts']
                pergunta=message['text']
                user_id=message['user']
                user_email=client.users_info(token=os.environ.get("SLACK_BOT_TOKEN"),user=user_id)['user']['profile']['email']
                user_nm_arr=user_email.split('@')
                user_nm=user_nm_arr[0]
            elif action!=None:
                user_id=body['user']['id']
                user_email=client.users_info(token=os.environ.get("SLACK_BOT_TOKEN"),user=user_id)['user']['profile']['email']
                user_nm_arr=user_email.split('@')
                user_nm=user_nm_arr[0]
                channel_id=body['channel']['id']
                thread=body['message_ts']          
                #verificação do tipo de ação, para alimentar a variável pergunta 
                if action['type']=='button': # verifica se o tipo da ação vem de um botão
                    pergunta=action['value']  #cria variável contendo a pergunta enviada para a Blue
                    #pergunta_texto=action['name']
                elif action['type']=='select': # verifica se o tipo da ação vem de um menu
                    pergunta=action['selected_options'][0]['value']  #cria variável contendo a pergunta enviada para a Blue 
                    #pergunta_texto=pergunta
            
            #chamada da rotina de inteligência
            retorno=cb.get_response(quest,pergunta,msg_notfound,user_id,linhas) # chama a rotina de inteligência para buscar a pergunta feita
            resposta=str(retorno[2]).replace('<@usuario>','<@' + user_id + '>') #a partir da resposta encontrada na instrução anterior  , substitui a experssão @usuário pelo usuário que está interagindo com a Blue    
            resposta=resposta.replace('\\n','\n')
            end_service=retorno[7] #guarda indicador de final de atendimento
            find_action=fndAct.get(linhas_action,retorno[1]) #verifica se é uma mensagem com ações retorno[1]= answer_id
            if find_action!={}:
                #trecho que trata itens que foram encontrados nas estruturas de dados de ações
                lst=[]
                for key, reg in find_action.items(): #montagem da estrutura de botões ou selects num loop para que seja passado para a api chat_postMessage
                    v_fallback= reg[1]
                    type_action=reg[5]
                    if type_action=='button': #verifica se o tipo da ação é um botão
                        lst.append({"name": str(reg[3]),"text": str(reg[3]),"type": "button","style": "primary","value": str(reg[4])})
                    elif type_action=='select': #verifica se o tipo da ação é um menu
                        lst.append({"text": str(reg[3]),"value": str(reg[4])})  
                if end_service=='FINAL_ATENDIMENTO':
                    assunto=pergunta
                    #assunto=pergunta_texto
                    result=client.chat_postMessage(channel=channel_id,text=resposta,thread_ts=thread) #envia resposta ao usuário numa mensagem simples
                    resposta=msg_end   
                    relat=rdAttendRegister.post(pergunta,retorno[8])
                    
                    #chamada de rotina de busca de categoria e subcategoria na tabela SUBCATEGORY_SN para enviar ao service now
                    pergunta_id=retorno[0] #guarda id da question pra buscar categoria e subcategoria do service now
                    find_sn=lstSubcat.get(pergunta_id) #chama rotina de busca de categoria e subcategoria relacionada a question
                elif end_service=='CONSULTA_INCIDENTE': # se for opção que direciona para consulta de incidentes
                    resposta_id=retorno[1] #guarda id da answer pra buscar serviço de negócio e categoria do service now
                    find_sn=lstBusSrvSN.get(resposta_id) #chama rotina de busca de serviço de negócio e categoria relacionada a answer
                    if find_sn!={}: #verifica se houve retorno de serviço de negócio e categoria
                        incs=''
                        for key, reg in find_sn.items():
                            #chama método de busca de incidentes
                                #resInc=fndInc.get(reg[0],reg[1])
                                resInc=fndInc.get(reg[0],key)
                                
                                if resInc!=0: #se o retorno de incidentes for diferente de 0, significa que o método encontrou incidentes abertos
                                    for inc in resInc['result']:
                                        dado_inc= "*Número:* " + str(inc['number']) + "\n*Incidente:* " + str(inc['short_description'])
                                        resImp=fndInc.getComp(inc['sys_id'])
                                        if resImp!=0:
                                            for imp in resImp['result']:
                                                dado_inc= dado_inc + "\n*Impacto:* " + str(imp['u_impact']) + "\n*Diagnóstico:* " +  str(imp['u_diagnosis'])
                                            
                                        if incs=='':
                                            incs= dado_inc
                                        else:
                                            incs= incs + '\n\n' + dado_inc

                    
                    if incs!='': #se o retorno de incidentes for diferente de 0, significa que o método encontrou incidentes abertos
                        #monta lista de incidentes encontrados
                        result=client.chat_postMessage(channel=channel_id,text=resposta + incs,thread_ts=thread)
                        resposta=msg_end   
                    else:
                        #senão retorna msg ao usuário indicando que não encontrou incidentes abertos
                        result=client.chat_postMessage(channel=channel_id,text="Tá tudo tranquilíssimo por aqui, sem nenhuma crise aberta no momento! #paz \nSe você identificou alguma instabilidade por aí, avisa a gente lá no canal #ask-noc",thread_ts=thread)
                        resposta=msg_end
                    find_sn={}
                    assunto=pergunta
                elif end_service=='CONSULTA_MUDANCA': # se for opção que direciona para consulta de incidentes
                    resposta_id=retorno[1] #guarda id da answer pra buscar serviço de negócio e categoria do service now
                    find_sn=lstBusSrvSN.getchg(resposta_id) #chama rotina de busca de serviço de negócio e categoria relacionada a answer
                    if find_sn!={}: #verifica se houve retorno de serviço de negócio e categoria
                        chg=''
                        for key, reg in find_sn.items():
                            #chama método de busca de incidentes
                            resChg=fndChgReq.get(reg[0])
                            if resChg!=0: #se o retorno de incidentes for diferente de 0, significa que o método encontrou incidentes abertos
                                for regs in resChg['result']:
                                    dado_chg= "*Número:* " + str(regs['number']) + "\n*Serviço de Negócio:* " + str(regs['business_service']['display_value']) + "\n*Descrição resumida:* " + str(regs['short_description']) + "\n*Indisponibilidade do serviço:* [Sim]\n*Data início planejada:* " + str(regs['start_date']) + "\n*Data fim planejada:* " + str(regs['end_date'])
                                    resImp=fndChgReq.getImp(regs['sys_id'])
                                    if resImp!=0:
                                        for imp in resImp['result']:
                                            dado_chg= dado_chg + "\n*Impacto:* " + str(imp['u_impact'])                   
                                    if chg=='' :
                                        chg= dado_chg
                                    else:
                                        chg=chg + '\n\n' + dado_chg
                                #retorna msg ao usuário indicando os incidentes encontrados
                                result=client.chat_postMessage(channel=channel_id,text=resposta + '\n' + chg,thread_ts=thread)
                                resposta=msg_end   
                            else:
                                #senão retorna msg ao usuário indicando que não encontrou incidentes abertos
                                result=client.chat_postMessage(channel=channel_id,text="Oi," + "<@" + user_id + ">! Confirmei aqui com os universitários e não tem nenhuma mudança que impacte o atendimento agendada pra hoje.",thread_ts=thread)
                                resposta=msg_end
                    find_sn={}
                    assunto=pergunta
                elif end_service=='NAO_ENCONTRADO':
                    assunto=pergunta
                    relat=rdQuestionNotFound.post(retorno[6],user_nm) #--registra relatório de questão não encontrada
                    resposta=str(retorno[2]).replace('<@usuario>','<@' + user_id + '>') #a partir da resposta encontrada na instrução anterior  , substitui a experssão @usuário pelo usuário que está interagindo com a Blue    
                    resposta=resposta.replace('\\n','\n')
                    
                if type_action.lower()=='button': #se o tipo de ação é um botão 
                    result=client.chat_postMessage(channel=channel_id,text=resposta,attachments=[{"text":'',"fallback": v_fallback,"callback_id": "acoes", "color": "#3AA3E3","attachment_type": "default","actions": lst}],thread_ts=thread)
                elif type_action.lower()=='select': #se o tipo de ação é um menu
                    result=client.chat_postMessage(channel=channel_id,text=resposta,attachments=[{"text":'',"fallback": v_fallback,"callback_id": "acoes", "color": "#3AA3E3","attachment_type": "default","actions":[{"name": "acoes", "text": "","type": "select", "options":lst}]}],thread_ts=thread)
            else:
                #trecho que trata itens que não foram encontrados nas estruturas de dados de ações 
                if end_service!='ABRE_ATENDIMENTO' and end_service!='SEM_SUCESSO': #Só deve enviar mensagem de resposta inicial se não for relacionado a abertura de chamado no service now ou atendimento sem sucesso
                    result=client.chat_postMessage(channel=channel_id,text=resposta,thread_ts=thread) #envia resposta ao usuário numa mensagem simples

                if end_service=='SEM_SUCESSO': # se for fim de atendimento sem sucesso
                    if find_sn!={}: #verifica se houve retorno de parâmetros que indicam abertura de chamado no service now
                        for key, reg in find_sn.items(): #traz valores para passar para a api do service now
                            #chama método que fará abertura de chamado no service now
                            resChamado=opnReq.post(user_id,'No',reg[0],reg[1],reg[2],'','')
                            #reg[0] => valor categoria
                            #reg[1] => nome subcategoria
                            #reg[2] => valor subcategoria
                        #grava informação de atendimento sem sucesso
                        relat=rdAttendNoSuccess.post(user_nm,"Atendimento sem sucesso",assunto,retorno[8],resChamado) #--registra relatório de atendimento sem sucesso
                        
                        msg_service='Um chamado em seu nome foi criado dentro do ServiceNow e encaminhado para equipe de atendimento. \nAguarde! Em breve entrarão em contato. \nNúmero do seu chamado: ' + '*' + resChamado + '*'
                        result=client.chat_postMessage(channel=channel_id,text=msg_service,thread_ts=thread) #envia mensagem aleatória
                    else:
                        relat=rdAttendNoSuccess.post(user_nm,"Atendimento sem sucesso",assunto,retorno[8],'') #--registra relatório de atendimento sem sucesso
                        result=client.chat_postMessage(channel=channel_id,text=resposta,thread_ts=thread) #envia mensagem aleatória
                    assunto=pergunta
                elif end_service=='SUCESSO': # se for fim de atendimento com sucesso
                    msg_ret_aleat=random.choice(aleat_lst) #seleciona uma mensagem aleatória para enviar no caso de atendimento com sucesso
                    result=client.chat_postMessage(channel=channel_id,text=msg_ret_aleat,thread_ts=thread) #envia mensagem aleatória
                    if find_sn!={}: #verifica se houve retorno de parâmetros que indicam abertura de chamado no service now
                        for key, reg in find_sn.items(): #traz valores para passar para a api do service now
                            #chama método de abertura chamado no service now, para contabilização do atendimento
                            resChamado=opnReq.post(user_id,'Yes',reg[0],reg[1],reg[2],'','')
                            #reg[0] => valor categoria
                            #reg[1] => nome subcategoria
                            #reg[2] => valor subcategoria
                        #grava informação de atendimento sem sucesso
                        relat=rdAttendSuccess.post(user_nm,"Atendimento com sucesso",assunto,retorno[8],resChamado) #--registra relatório de atendimento com sucesso
                    else:
                        
                        relat=rdAttendSuccess.post(user_nm,"Atendimento com sucesso",assunto,retorno[8],'') #--registra relatório de atendimento com sucesso
                elif end_service=='REDIRECIONA': # se for fim de atendimento com redirecionamento
                    assunto=pergunta
                    relat=rdAttendanceRedirected.post(pergunta,retorno[5],user_nm) #gravação de relatório de redirecionamento
                
                elif end_service=='ABRE_ATENDIMENTO': #abertura de chamados que não tiveram origem em uma tentativa de atendimento pela Blue, nesses casos ela abre chamado diretamente sem perguntar se ajudou ou não, por isso esse tipo de atendimento é sempre com sucesso
                    assunto=pergunta
                    #chamada de rotina de busca de categoria e subcategoria para enviar ao service now
                    pergunta_id=retorno[0] #guarda id da question pra buscar categoria e subcategoria do service now
                    find_sn=lstSubcat.get(pergunta_id) #chama rotina de busca de categoria e subcategoria relacionada a question
                    
                    if find_sn!={}:
                        for key, reg in find_sn.items(): #traz valores para passar para a api do service now
                            #chama método de abertura de chamado no service now
                            resChamado=opnReq.post(user_id,'No',reg[0],reg[1],reg[2],reg[3],reg[4])
                            #reg[0] => valor categoria
                            #reg[1] => nome subcategoria
                            #reg[2] => valor subcategoria
                            #reg[3] => nome campo parametrizado
                            #reg[4] => valor campo parametrizado
                        #registra atendimento na collection de atendimentos com sucesso                        
                        relat=rdAttendSuccess.post(user_nm,"Atendimento com sucesso",assunto,retorno[8],resChamado) #--registra relatório de atendimento com sucesso
                        result=client.chat_postMessage(channel=channel_id,text='Espere um momento abriendo chamdo..',thread_ts=thread)
                        msg_service='Este assunto requer um chamado no ServiceNow. \nUm chamado em seu nome foi criado e encaminhado para equipe de atendimento. \nAguarde! Em breve entrarão em contato. \nNúmero do seu chamado: ' + '*' + resChamado + '*'
                        result=client.chat_postMessage(channel=channel_id,text=msg_service,thread_ts=thread) #envia indicando o chamado
                    
            if retorno[5]!='None': #verifica se tem canal de direcionamento
                result=client.chat_postMessage(channel=retorno[5],text=str(retorno[4]).replace('<@usuario>','<@' + user_id + '>').replace('Assunto:', ' Assunto: ' + assunto.upper()))  # envia mensagem direcionando atendimento para outro canal
            


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
