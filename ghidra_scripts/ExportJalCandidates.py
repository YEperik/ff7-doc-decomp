# Ghidra Jython script for large PS2 projects.
# Exports JAL/JALR instructions in bounded CSV parts, with local context and target details.
# This is diagnostic only; it does not patch instructions or prove they are invalid.
from java.io import File, FileWriter, BufferedWriter

out_dir = askDirectory("Choose output folder for JAL reports", "Select")
chunk_text = askString("Rows per CSV part", "100000")
include_jalr = askYesNo("Include JALR?", "Include indirect JALR instructions too?")
try:
    chunk_limit = int(chunk_text.strip())
    if chunk_limit < 1:
        raise ValueError("chunk size must be >= 1")
except:
    popup("Invalid chunk size. Enter an integer greater than zero.")
    raise Exception("Invalid chunk size")

listing = currentProgram.getListing()
memory = currentProgram.getMemory()
fm = currentProgram.getFunctionManager()
monitor.setMessage("Scanning instructions for JAL/JALR...")
monitor.initialize(0)

headers = ["address", "address_offset", "bytes", "mnemonic", "operands", "previous_instruction",
           "next_instruction", "function", "source_block", "flow_targets", "target_blocks",
           "target_executable", "reference_types"]

def csv_cell(value):
    value = str(value).replace('"', '""').replace('\r', ' ').replace('\n', ' ')
    return '"' + value + '"'

def instruction_text(ins):
    if ins is None:
        return ""
    return str(ins.getAddress()) + ": " + ins.toString()

class ChunkWriter:
    def __init__(self, folder, max_rows):
        self.folder = folder
        self.max_rows = max_rows
        self.part = 0
        self.rows = 0
        self.total = 0
        self.writer = None
        self.file_writer = None
        self.open_part()
    def open_part(self):
        if self.file_writer is not None:
            self.file_writer.close()
        self.part += 1
        f = File(self.folder, "jal_triage_%03d.csv" % self.part)
        self.file_writer = BufferedWriter(FileWriter(f))
        self.file_writer.write(",".join([csv_cell(h) for h in headers]) + "\n")
        self.rows = 0
    def write(self, row):
        if self.rows >= self.max_rows:
            self.open_part()
        self.file_writer.write(",".join([csv_cell(v) for v in row]) + "\n")
        self.rows += 1
        self.total += 1
    def close(self):
        if self.file_writer is not None:
            self.file_writer.close()

out = ChunkWriter(out_dir, chunk_limit)
scanned = 0
try:
    instructions = listing.getInstructions(True)
    while instructions.hasNext() and not monitor.isCancelled():
        ins = instructions.next()
        scanned += 1
        if (scanned % 50000) == 0:
            monitor.setMessage("Scanned %d instructions; exported %d rows" % (scanned, out.total))
        mnemonic = ins.getMnemonicString().upper()
        if mnemonic != "JAL" and not (include_jalr and mnemonic == "JALR"):
            continue
        targets, target_blocks, executable, ref_types = [], [], [], []
        for ref in ins.getReferencesFrom():
            try:
                ref_types.append(str(ref.getReferenceType()))
                if ref.getReferenceType().isCall() or ref.getReferenceType().isJump():
                    targets.append(str(ref.getToAddress()))
            except:
                pass
        if not targets:
            for target in ins.getFlows():
                targets.append(str(target))
        for target in targets:
            try:
                addr = currentProgram.getAddressFactory().getAddress(target)
                block = memory.getBlock(addr) if addr is not None else None
                target_blocks.append(block.getName() if block is not None else "<no block>")
                executable.append(str(block.isExecute()) if block is not None else "unknown")
            except:
                target_blocks.append("<unresolved>")
                executable.append("unknown")
        if not targets:
            targets = ["<no resolved flow target>"]
            target_blocks = ["<unresolved>"]
            executable = ["unknown"]
        func = fm.getFunctionContaining(ins.getAddress())
        func_name = func.getName() if func is not None else "<no function>"
        block = memory.getBlock(ins.getAddress())
        source_block = block.getName() if block is not None else "<no block>"
        operands = []
        for i in range(ins.getNumOperands()):
            operands.append(ins.getDefaultOperandRepresentation(i))
        prev_ins = listing.getInstructionBefore(ins.getAddress())
        next_ins = listing.getInstructionAfter(ins.getAddress())
        for i in range(len(targets)):
            out.write([str(ins.getAddress()), "0x%X" % ins.getAddress().getOffset(),
                       ''.join(['%02X' % (b & 0xff) for b in ins.getBytes()],), mnemonic,
                       " ".join(operands), instruction_text(prev_ins), instruction_text(next_ins),
                       func_name, source_block, targets[i], target_blocks[i] if i < len(target_blocks) else "",
                       executable[i] if i < len(executable) else "unknown", ";".join(ref_types)])
finally:
    out.close()

popup("Finished. Scanned %d instructions; exported %d rows into %d CSV part(s) in:\n%s\n\nThese are triage records, not confirmed bad instructions." %
      (scanned, out.total, out.part, out_dir.getAbsolutePath()))
