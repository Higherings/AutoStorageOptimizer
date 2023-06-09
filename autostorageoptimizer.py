# igarcia 2023-05
# Version 1.0.0
# Automation for Compute Optimizer Recommendations for EBS (Storage)
# It will change the EBS Volumen Type to a Recommendation of the AWS Compute Optimizer Service and send an email about it
# You can set a TAG and Value for the EBS volumes that this Lambda will SKIP, by default it covers all EBS volumes

import os
import json
import boto3

RISK = os.environ['RISK'] #de 0 a 4, 0 es sin riesgo y 4 es mucho riesgo (No Risk, Very Low, Low, Medium, High) Recomendado 1
TAGBUSQUEDA = os.environ['TAGBUSQUEDA']
TAGVALOR = os.environ['TAGVALOR']
TOPIC = os.environ['TOPIC']
CORREO = os.environ['CORREO']
MENSAJE = ""
EXCEPTIONS = os.getenv('EXCEPTIONS', default='-').split(',') # Valid values: io1, io2, gp2, gp3, st1, sc1, standard
EXCEPTIONS = [ exception.strip().lower() for exception in EXCEPTIONS] # To trimm and lowercase
risk_text = {"0":"No Risk", "1":"Very Low Risk", "2":"Low Risk", "3":"Medium Risk", "4":"High Risk", "5":"Very High Risk"}

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
co_client = boto3.client('compute-optimizer')
sns = boto3.resource('sns')

def review_compute_optimizer_recos(vol):
	global MENSAJE
	cambio = 0
	response = ""
	vol_id = vol['volumeArn'].split('/')[1] #Volume ID
	volume = ec2.Volume(vol_id)
	ec2_instance = ec2.Instance(volume.attachments[0]['InstanceId'])
	ec2_name = '-'
	ec2_tags = ec2_instance.tags
	for tag in ec2_tags:
		if tag['Key'] == 'Name':
			ec2_name = tag['Value']
					
	to_do = True # Flag to determine if Volume will be examined
	vol_tags = volume.tags
	if vol_tags:
		for tag in vol_tags:
			if tag['Key'] == TAGBUSQUEDA:
				if tag['Value'] == TAGVALOR:
					to_do = False

	if to_do:
		for option in vol['volumeRecommendationOptions']:
			new_type = option['configuration'].get('volumeType','gp3')
			new_iops = option['configuration'].get('volumeBaselineIOPS',3000)
			new_throughput = option['configuration'].get('volumeBaselineThroughput',125)
			if new_type in EXCEPTIONS:
				continue
			if (int(option['performanceRisk']) <= int(RISK)): # El riesgo debe ser aceptable
				new_type = option['configuration'].get('volumeType','gp3')
				new_iops = option['configuration'].get('volumeBaselineIOPS',3000)
				new_throughput = option['configuration'].get('volumeBaselineThroughput',125)
				if volume.state == 'in-use':
					try:
						if new_type == 'gp3':
							response = ec2_client.modify_volume(VolumeId=vol_id,VolumeType=new_type,Iops=new_iops,Throughput=new_throughput)
						elif new_type in ['io1','io2']:
							response = ec2_client.modify_volume(VolumeId=vol_id,VolumeType=new_type,Iops=new_iops)
						else:
							response = ec2_client.modify_volume(VolumeId=vol_id,VolumeType=new_type)
						cambio = 1
						new_type = response['VolumeModification'].get('TargetVolumeType',new_type)
						new_iops = response['VolumeModification'].get('TargetIops','-')
						new_throughput = response['VolumeModification'].get('TargetThroughput','-')
						MENSAJE = MENSAJE + "Info: Instance " + ec2_name + ", EBS volume " + vol_id + " changed to " + new_type + " with IOPS: "+str(new_iops)+" and Throughput: "+str(new_throughput)+" MiB/s\n"
						print("Se modificó Instancia {} EBS {} a {} IOPS {} Throughput {} MiB/s".format(ec2_name, vol_id, new_type, new_iops, new_throughput))
						break
					except:
						cambio = 0
						MENSAJE = MENSAJE + "Error: Instance " + ec2_name + ", EBS volume " + vol_id + " NOT changed to " + new_type + " with IOPS: "+str(new_iops)+" and Throughput: "+str(new_throughput)+" MiB/s\n"
						print(response)
						print("Error el modificar Instancia {} EBS {} a {} IOPS {} Throughput {} MiB/s".format(ec2_name, vol_id, new_type, new_iops, new_throughput))
						break

		if response == "":
			MENSAJE = MENSAJE + "Info: Instance " + ec2_name + ", EBS volume " + vol_id + " with no viable options. \n"
	else:
		MENSAJE = MENSAJE + "Info: Nothing to do for Instance " + ec2_name + ", EBS volume " + vol_id + "\n"
		print("No se modificó Instancia {} - {}.".format(ec2_name, vol_id))

	return cambio

def lambda_handler(event, context):
	total = 0
	cambios = 0
	global MENSAJE

	R_TYPE = ['NotOptimized']

	MENSAJE = ""
	ebs_recos = co_client.get_ebs_volume_recommendations(filters=[{'name':'Finding','values':R_TYPE}])
	for vol in ebs_recos['volumeRecommendations']:
		total+=1
		cambios = cambios + review_compute_optimizer_recos(vol)

	while 'nextToken' in ebs_recos: #Pagineo
		ebs_recos = co_client.get_ebs_volume_recommendations(
			nextToken=ebs_recos['nextToken'],
			filters=[{'name':'Finding','values':R_TYPE}]
		)
		for vol in ebs_recos['volumeRecommendations']:
			total+=1
			cambios = cambios + review_compute_optimizer_recos(vol)

	the_message = "EBS Volumes updated "+str(cambios)+" of "+str(total)+" total recommendations:\n"
	print("Se realizaron {} cambios con éxito de un total de {} sugeridos.".format(cambios,total))
	print("Limite indicador de Riesgo: {}".format(risk_text[RISK]))
	try:
		if CORREO != "not@notify.me":
			the_topic = sns.Topic(TOPIC)
			the_message = the_message + MENSAJE
			the_message = the_message + "\nDefined risk threshold to modify EBS volumes: " + risk_text[RISK] + "." + "\nMore information on Lambda log."
			response = the_topic.publish(Subject="AutoStorageOptimizer Notification", Message=the_message)
	except:
		print(response)
		print("Fallo al enviar mensaje por SNS.")
	return {
		'statusCode': 200,
		'body': json.dumps(
			'Lambda finalizada exitosamente.'
		)
	}