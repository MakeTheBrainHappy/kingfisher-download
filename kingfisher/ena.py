import subprocess
import logging
import os

class AsperaEnaDownloader:
    def download(self, run_id, output_directory, quiet=False, ascp_args='', ssh_key='linux'):
        if ssh_key == 'linux':
            ssh_key_file = '$HOME/.aspera/connect/etc/asperaweb_id_dsa.openssh'
        elif ssh_key == 'osx':
            ssh_key_file = '$HOME/Applications/Aspera Connect.app/Contents/\
                Resources/asperaweb_id_dsa.openssh'
        else:
            ssh_key_file = ssh_key
        logging.info("Using aspera ssh key file: {}".format(ssh_key_file))

        # Get the textual representation of the run. We specifically need the
        # fastq_ftp bit
        logging.info("Querying ENA for FTP paths for {}..".format(run_id))
        query_url = "https://www.ebi.ac.uk/ena/portal/api/filereport?accession={}&" \
            "result=read_run&fields=fastq_ftp".format(
            run_id)
        logging.debug("Querying '{}'".format(query_url))
        text = subprocess.check_output(
            "curl --silent '{}'".format(query_url), shell=True)

        ftp_urls = []
        header = True
        logging.debug("Found text from ENA API: {}".format(text))
        for line in text.decode('utf8').split('\n'):
            logging.debug("Parsing line: {}".format(line))
            if header:
                header = False
            else:
                if line == '':
                    continue
                fastq_ftp = line.split('\t')[1]
                for url in fastq_ftp.split(';'):
                    if url.strip() != '':
                        ftp_urls.append(url.strip())
        if len(ftp_urls) == 0:
            # One (current) example of this is DRR086621
            logging.error(
                "No FTP download URLs found for run {}, cannot continue".format(
                    run_id))
            return False
        else:
            logging.debug("Found {} FTP URLs for download: {}".format(
                len(ftp_urls), ", ".join(ftp_urls)))

        logging.info("Downloading {} FTP read set(s): {}".format(
            len(ftp_urls), ", ".join(ftp_urls)))

        aspera_commands = []
        output_files = []
        for url in ftp_urls:
            quiet_args = ''
            if quiet:
                quiet_args = ' -Q'
            output_file = os.path.join(output_directory, os.path.basename(url))
            logging.debug("Getting output file {}".format(output_file))
            cmd = "ascp{} -T -l 300m -P33001 {} -i {} era-fasp@fasp.sra.ebi.ac.uk:{} {}".format(
                quiet_args,
                ascp_args,
                ssh_key_file,
                url.replace('ftp.sra.ebi.ac.uk', ''),
                output_directory)
            logging.info("Running command: {}".format(cmd))
            try:
                subprocess.check_call(cmd, shell=True)
            except Exception as e:
                logging.warn("Error downloading from ENA with ASCP: {}".format(e))
                return False
            output_files.append(output_file)
        
        return output_files