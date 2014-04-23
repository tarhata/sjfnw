import logging
logger = logging.getLogger('sjfnw')

def log_queries(queries):
  output = '\n'
  count = 0
  for q in queries:
    count = count + 1
    output = output + str(count) + ') (' + q['time'] + ') ' + q['sql'] + '\n'
  output = output + str(count) + ' TOTAL QUERIES'

  logger.info(output)

